from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from app.core.backup.services import BackupError, restore_local_backup


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
        backup_path = Path(options['backup_path']).expanduser()
        try:
            result = restore_local_backup(
                backup_path.name,
                output_dir=backup_path.parent,
                restore_media=options['restore_media'],
                skip_migrate=options['skip_migrate'],
                allow_non_local_db=options['allow_non_local_db'],
                confirmed=options['yes'],
                verbosity=options.get('verbosity', 1),
            )
        except BackupError as exc:
            raise CommandError(str(exc))

        if options['restore_media']:
            self.stdout.write('Archivos media restaurados: {}'.format(result['restored_media']))
        self.stdout.write(self.style.SUCCESS('Base local restaurada desde: {}'.format(result['path'])))
