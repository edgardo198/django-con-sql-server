import json
import os
import re
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

import django
from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.utils import timezone


BACKUP_PREFIX = 'erp-local-backup'
BACKUP_EXCLUDES = [
    'contenttypes',
    'auth.permission',
    'admin.logentry',
    'sessions.session',
]


class BackupError(Exception):
    pass


def env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def default_backup_dir():
    return os.getenv('LOCAL_BACKUP_DIR') or os.path.join(settings.BASE_DIR, 'local_backups')


def resolve_backup_dir(output_dir=None):
    return Path(output_dir or default_backup_dir()).expanduser().resolve()


def safe_label(value):
    value = (value or '').strip().lower()
    value = re.sub(r'[^a-z0-9_-]+', '-', value)
    return value.strip('-')


def is_sqlite_database():
    return connection.settings_dict.get('ENGINE', '').endswith('sqlite3')


def database_name():
    return connection.settings_dict.get('NAME') or ''


def is_local_database():
    database = settings.DATABASES['default']
    engine = database.get('ENGINE', '')
    if engine.endswith('sqlite3'):
        return True

    host = (database.get('HOST') or '').strip().lower()
    return host in ('', 'localhost', '127.0.0.1', '::1')


def add_media_files(zip_file, media_root):
    root = Path(media_root)
    if not root.exists() or not root.is_dir():
        return 0

    added = 0
    for file_path in root.rglob('*'):
        if not file_path.is_file():
            continue
        zip_file.write(file_path, Path('media') / file_path.relative_to(root))
        added += 1
    return added


def cleanup_old_backups(output_dir, keep, current_path):
    if keep <= 0:
        return 0

    backups = sorted(
        output_dir.glob('{}-*.zip'.format(BACKUP_PREFIX)),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    removed = 0
    current_path = current_path.resolve()

    for backup in backups[keep:]:
        if backup.resolve() == current_path:
            continue
        backup.unlink(missing_ok=True)
        removed += 1

    return removed


def create_local_backup(output_dir=None, keep=None, label='', include_media=True):
    output_path = resolve_backup_dir(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    created_at = timezone.now()
    label = safe_label(label)
    filename_parts = [
        BACKUP_PREFIX,
        created_at.strftime('%Y%m%d-%H%M%S'),
    ]
    if label:
        filename_parts.append(label)
    backup_path = output_path / ('-'.join(filename_parts) + '.zip')

    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        data_path = temp_path / 'data.json'

        dump_args = [
            '--natural-foreign',
            '--natural-primary',
            '--indent',
            '2',
        ]
        for exclude in BACKUP_EXCLUDES:
            dump_args.extend(['--exclude', exclude])

        with data_path.open('w', encoding='utf-8') as dump_file:
            call_command('dumpdata', *dump_args, stdout=dump_file)

        manifest = {
            'format': 'erp-local-backup-v1',
            'created_at': created_at.isoformat(),
            'django_version': django.get_version(),
            'database': {
                'engine': connection.settings_dict.get('ENGINE', ''),
                'name': str(database_name()),
                'host': connection.settings_dict.get('HOST', ''),
                'port': connection.settings_dict.get('PORT', ''),
            },
            'contains': {
                'data_json': True,
                'sqlite_file': False,
                'media': False,
            },
            'excluded': BACKUP_EXCLUDES,
        }

        with zipfile.ZipFile(backup_path, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zip_file:
            zip_file.write(data_path, 'data.json')

            if is_sqlite_database() and database_name() and Path(database_name()).exists():
                zip_file.write(database_name(), 'database.sqlite3')
                manifest['contains']['sqlite_file'] = True

            if include_media:
                media_count = add_media_files(zip_file, settings.MEDIA_ROOT)
                manifest['contains']['media'] = media_count > 0
                manifest['media_files'] = media_count

            zip_file.writestr(
                'manifest.json',
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )

    retention = env_int('LOCAL_BACKUP_RETENTION', 14) if keep is None else max(int(keep), 0)
    removed = cleanup_old_backups(output_path, retention, backup_path)
    return {
        'path': backup_path,
        'filename': backup_path.name,
        'removed': removed,
        'manifest': manifest,
    }


def safe_backup_path(filename, output_dir=None, must_exist=True):
    if not filename or Path(filename).name != filename:
        raise BackupError('Nombre de respaldo no valido.')
    if not filename.startswith('{}-'.format(BACKUP_PREFIX)) or not filename.endswith('.zip'):
        raise BackupError('El archivo no parece un respaldo local valido.')

    root = resolve_backup_dir(output_dir)
    backup_path = (root / filename).resolve()
    if root not in backup_path.parents:
        raise BackupError('Ruta de respaldo no permitida.')
    if must_exist and not backup_path.exists():
        raise BackupError('No existe el respaldo solicitado.')
    return backup_path


def read_backup_manifest(backup_path):
    try:
        with zipfile.ZipFile(backup_path, 'r') as zip_file:
            if 'manifest.json' not in zip_file.namelist():
                return {}
            with zip_file.open('manifest.json') as manifest_file:
                return json.loads(manifest_file.read().decode('utf-8'))
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError):
        return {}


def format_file_size(size):
    units = ['B', 'KB', 'MB', 'GB']
    value = float(size or 0)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return '{:.1f} {}'.format(value, unit) if unit != 'B' else '{} B'.format(int(value))
        value /= 1024


def get_backup_info(backup_path):
    manifest = read_backup_manifest(backup_path)
    stat = backup_path.stat()
    contains = manifest.get('contains') or {}
    database = manifest.get('database') or {}
    return {
        'filename': backup_path.name,
        'path': backup_path,
        'size': stat.st_size,
        'size_label': format_file_size(stat.st_size),
        'modified_at': timezone.datetime.fromtimestamp(stat.st_mtime, tz=timezone.get_current_timezone()),
        'created_at': manifest.get('created_at') or '',
        'django_version': manifest.get('django_version') or '',
        'database_engine': database.get('engine') or '',
        'database_name': database.get('name') or '',
        'contains_media': bool(contains.get('media')),
        'media_files': manifest.get('media_files', 0),
        'manifest': manifest,
    }


def list_local_backups(output_dir=None):
    root = resolve_backup_dir(output_dir)
    if not root.exists():
        return []
    return [
        get_backup_info(backup_path)
        for backup_path in sorted(
            root.glob('{}-*.zip'.format(BACKUP_PREFIX)),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        if backup_path.is_file()
    ]


def delete_local_backup(filename, output_dir=None):
    backup_path = safe_backup_path(filename, output_dir=output_dir)
    backup_path.unlink()
    return backup_path


def safe_extract_media(zip_file, media_root):
    root = Path(media_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    restored = 0

    for member in zip_file.infolist():
        if member.is_dir() or not member.filename.startswith('media/'):
            continue

        relative_name = member.filename[len('media/'):]
        if not relative_name:
            continue

        destination = (root / relative_name).resolve()
        if root not in destination.parents and destination != root:
            raise BackupError('El respaldo contiene una ruta de media insegura: {}'.format(member.filename))

        destination.parent.mkdir(parents=True, exist_ok=True)
        with zip_file.open(member) as source, destination.open('wb') as target:
            target.write(source.read())
        restored += 1

    return restored


def restore_local_backup(
    filename,
    output_dir=None,
    restore_media=False,
    skip_migrate=False,
    allow_non_local_db=False,
    confirmed=False,
    verbosity=1,
):
    if not confirmed:
        raise BackupError('Operacion destructiva: confirma la restauracion local.')
    if os.getenv('RENDER'):
        raise BackupError('No ejecutes restauraciones locales dentro de Render.')
    if not allow_non_local_db and not is_local_database():
        raise BackupError('La base configurada no parece local.')

    backup_path = safe_backup_path(filename, output_dir=output_dir)
    with zipfile.ZipFile(backup_path, 'r') as zip_file:
        names = set(zip_file.namelist())
        if 'data.json' not in names:
            raise BackupError('El respaldo no contiene data.json.')

        with TemporaryDirectory() as temp_dir:
            temp_data_path = Path(temp_dir) / 'data.json'
            with zip_file.open('data.json') as source, temp_data_path.open('wb') as target:
                target.write(source.read())

            if not skip_migrate:
                call_command('migrate', interactive=False, verbosity=0)

            call_command('flush', interactive=False, verbosity=0)
            call_command('loaddata', str(temp_data_path), verbosity=verbosity)

            restored_media = 0
            if restore_media:
                restored_media = safe_extract_media(zip_file, settings.MEDIA_ROOT)

    return {
        'path': backup_path,
        'filename': backup_path.name,
        'restored_media': restored_media,
    }
