import os
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from app.core.sync.management.commands.sync_with_remote import normalize_remote_url


def is_local_database():
    database = settings.DATABASES['default']
    engine = database.get('ENGINE', '')
    if engine.endswith('sqlite3'):
        return True

    host = (database.get('HOST') or '').strip().lower()
    return host in ('', 'localhost', '127.0.0.1', '::1')


class Command(BaseCommand):
    help = 'Borra datos locales y reconstruye la base desde Render usando sync pull.'

    def add_arguments(self, parser):
        parser.add_argument('--remote', default=os.getenv('SYNC_REMOTE_URL'))
        parser.add_argument('--token', default=os.getenv('SYNC_API_TOKEN') or os.getenv('DJANGO_SYNC_TOKEN'))
        parser.add_argument('--timeout', type=int, default=int(os.getenv('SYNC_TIMEOUT', '30')))
        parser.add_argument('--pull-limit', type=int, default=int(os.getenv('SYNC_PULL_BATCH_SIZE', '500')))
        parser.add_argument('--yes', action='store_true', help='Confirma el borrado de datos locales.')
        parser.add_argument(
            '--allow-non-local-db',
            action='store_true',
            help='Permite borrar una base cuyo HOST no es localhost/127.0.0.1.',
        )

    def handle(self, *args, **options):
        remote_url = options['remote']
        token = options['token']

        if not options['yes']:
            raise CommandError('Operacion destructiva: agrega --yes para confirmar el borrado local.')
        if not remote_url:
            raise CommandError('Debe configurar SYNC_REMOTE_URL o pasar --remote.')
        if not token:
            raise CommandError('Debe configurar SYNC_API_TOKEN o pasar --token.')
        if not options['allow_non_local_db'] and not is_local_database():
            raise CommandError(
                'La base configurada no parece local. Usa --allow-non-local-db solo si estas seguro.'
            )
        if os.getenv('RENDER'):
            raise CommandError('No ejecutes este comando dentro de Render.')

        remote_url = normalize_remote_url(remote_url)
        session = requests.Session()
        session.headers.update({'X-Sync-Token': token})

        try:
            response = session.get(urljoin(remote_url, 'sync/status/'), timeout=options['timeout'])
            response.raise_for_status()
        except Exception as exc:
            raise CommandError(
                'Render no esta listo para sincronizar. No se borro nada local. Detalle: {}'.format(exc)
            )

        self.stdout.write(self.style.WARNING('Render respondio OK. Borrando datos locales...'))
        call_command('flush', interactive=False, verbosity=0)

        self.stdout.write('Descargando datos desde Render...')
        call_command(
            'sync_with_remote',
            '--pull-only',
            '--remote',
            remote_url,
            '--token',
            token,
            '--pull-limit',
            str(options['pull_limit']),
            verbosity=options.get('verbosity', 1),
        )
        self.stdout.write(self.style.SUCCESS('Base local reconstruida desde Render.'))
