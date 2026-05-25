import os
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


def is_local_database():
    database = settings.DATABASES['default']
    engine = database.get('ENGINE', '')
    if engine.endswith('sqlite3'):
        return True

    host = (database.get('HOST') or '').strip().lower()
    return host in ('', 'localhost', '127.0.0.1', '::1')


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
            raise CommandError('El respaldo contiene una ruta de media insegura: {}'.format(member.filename))

        destination.parent.mkdir(parents=True, exist_ok=True)
        with zip_file.open(member) as source, destination.open('wb') as target:
            target.write(source.read())
        restored += 1

    return restored


class Command(BaseCommand):
    help = 'Restaura una base local desde un ZIP creado con local_backup.'

    def add_arguments(self, parser):
        parser.add_argument('backup_path')
        parser.add_argument('--yes', action='store_true', help='Confirma el borrado de datos locales.')
        parser.add_argument('--restore-media', action='store_true', help='Restaura archivos media incluidos en el ZIP.')
        parser.add_argument('--skip-migrate', action='store_true', help='No ejecutar migraciones antes de restaurar.')
        parser.add_argument(
            '--allow-non-local-db',
            action='store_true',
            help='Permite restaurar sobre una base cuyo HOST no es localhost/127.0.0.1.',
        )

    def handle(self, *args, **options):
        if not options['yes']:
            raise CommandError('Operacion destructiva: agrega --yes para confirmar la restauracion local.')
        if os.getenv('RENDER'):
            raise CommandError('No ejecutes este comando dentro de Render.')
        if not options['allow_non_local_db'] and not is_local_database():
            raise CommandError(
                'La base configurada no parece local. Usa --allow-non-local-db solo si estas seguro.'
            )

        backup_path = Path(options['backup_path']).expanduser().resolve()
        if not backup_path.exists():
            raise CommandError('No existe el respaldo: {}'.format(backup_path))

        with zipfile.ZipFile(backup_path, 'r') as zip_file:
            names = set(zip_file.namelist())
            if 'data.json' not in names:
                raise CommandError('El respaldo no contiene data.json.')

            with TemporaryDirectory() as temp_dir:
                temp_data_path = Path(temp_dir) / 'data.json'
                with zip_file.open('data.json') as source, temp_data_path.open('wb') as target:
                    target.write(source.read())

                if not options['skip_migrate']:
                    call_command('migrate', interactive=False, verbosity=0)

                self.stdout.write(self.style.WARNING('Borrando datos locales...'))
                call_command('flush', interactive=False, verbosity=0)

                self.stdout.write('Cargando datos del respaldo...')
                call_command('loaddata', str(temp_data_path), verbosity=options.get('verbosity', 1))

                if options['restore_media']:
                    restored = safe_extract_media(zip_file, settings.MEDIA_ROOT)
                    self.stdout.write('Archivos media restaurados: {}'.format(restored))

        self.stdout.write(self.style.SUCCESS('Base local restaurada desde: {}'.format(backup_path)))
