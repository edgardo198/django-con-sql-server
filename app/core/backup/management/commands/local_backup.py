import os

from django.core.management.base import BaseCommand, CommandError

from app.core.backup.services import BackupError, create_local_backup, default_backup_dir, env_bool, env_int


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
        try:
            result = create_local_backup(
                output_dir=options['output_dir'],
                keep=options['keep'],
                label=options['label'],
                include_media=not options['no_media'],
            )
        except BackupError as exc:
            raise CommandError(str(exc))

        self.stdout.write(self.style.SUCCESS('Respaldo local creado: {}'.format(result['path'])))
        if result['removed']:
            self.stdout.write('Respaldos antiguos eliminados por retencion: {}'.format(result['removed']))
