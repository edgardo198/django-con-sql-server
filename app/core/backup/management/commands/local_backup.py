import json
import os
import re
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

import django
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone


BACKUP_PREFIX = 'erp-local-backup'
BACKUP_EXCLUDES = [
    'contenttypes',
    'auth.permission',
    'admin.logentry',
    'sessions.session',
]


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


def safe_label(value):
    value = (value or '').strip().lower()
    value = re.sub(r'[^a-z0-9_-]+', '-', value)
    return value.strip('-')


def is_sqlite_database():
    return connection.settings_dict.get('ENGINE', '').endswith('sqlite3')


def database_name():
    return connection.settings_dict.get('NAME') or ''


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


class Command(BaseCommand):
    help = 'Crea un respaldo local portable de la base de datos y, opcionalmente, de la carpeta media.'

    def add_arguments(self, parser):
        parser.add_argument('--output-dir', default=default_backup_dir())
        parser.add_argument('--keep', type=int, default=env_int('LOCAL_BACKUP_RETENTION', 14))
        parser.add_argument('--label', default=os.getenv('LOCAL_BACKUP_LABEL', ''))
        parser.add_argument(
            '--no-media',
            action='store_true',
            default=not env_bool('LOCAL_BACKUP_INCLUDE_MEDIA', True),
            help='No incluir la carpeta media en el ZIP.',
        )

    def handle(self, *args, **options):
        output_dir = Path(options['output_dir']).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        created_at = timezone.now()
        label = safe_label(options['label'])
        filename_parts = [
            BACKUP_PREFIX,
            created_at.strftime('%Y%m%d-%H%M%S'),
        ]
        if label:
            filename_parts.append(label)
        backup_path = output_dir / ('-'.join(filename_parts) + '.zip')

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

                if not options['no_media']:
                    media_count = add_media_files(zip_file, settings.MEDIA_ROOT)
                    manifest['contains']['media'] = media_count > 0
                    manifest['media_files'] = media_count

                zip_file.writestr(
                    'manifest.json',
                    json.dumps(manifest, ensure_ascii=False, indent=2),
                )

        removed = cleanup_old_backups(output_dir, max(options['keep'], 0), backup_path)

        self.stdout.write(self.style.SUCCESS('Respaldo local creado: {}'.format(backup_path)))
        if removed:
            self.stdout.write('Respaldos antiguos eliminados por retencion: {}'.format(removed))
