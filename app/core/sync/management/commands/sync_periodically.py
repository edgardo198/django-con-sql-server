import os
import time
from urllib.parse import urljoin

import requests
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from app.core.sync.management.commands.sync_with_remote import normalize_remote_url
from app.core.sync.models import SyncOutbox
from app.core.sync.registry import get_outgoing_model_labels_for_current_node
from app.core.sync.services import get_configured_remote_url, get_configured_sync_token, is_remote_sync_enabled


def env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


class Command(BaseCommand):
    help = 'Ejecuta sincronizacion periodica con Render cuando hay conexion.'

    def add_arguments(self, parser):
        parser.add_argument('--remote', default=os.getenv('SYNC_REMOTE_URL'))
        parser.add_argument('--token', default=os.getenv('SYNC_API_TOKEN') or os.getenv('DJANGO_SYNC_TOKEN'))
        parser.add_argument('--interval', type=int, default=env_int('SYNC_INTERVAL_SECONDS', 300))
        parser.add_argument('--retry', type=int, default=env_int('SYNC_RETRY_SECONDS', 30))
        parser.add_argument('--debounce', type=int, default=env_int('SYNC_DEBOUNCE_SECONDS', 5))
        parser.add_argument('--timeout', type=int, default=env_int('SYNC_TIMEOUT', 30))
        parser.add_argument('--connectivity-timeout', type=int, default=env_int('SYNC_CONNECTIVITY_TIMEOUT_SECONDS', 10))
        parser.add_argument('--limit', type=int, default=env_int('SYNC_BATCH_SIZE', 250))
        parser.add_argument('--pull-limit', type=int, default=env_int('SYNC_PULL_BATCH_SIZE', 500))
        parser.add_argument('--lock-ttl', type=int, default=env_int('SYNC_LOCK_TTL_SECONDS', 900))
        parser.add_argument('--once', action='store_true', help='Ejecuta un ciclo y termina.')
        parser.add_argument('--max-runs', type=int, default=0, help='Cantidad maxima de ciclos exitosos. 0 = infinito.')

    def handle(self, *args, **options):
        remote_url = options['remote'] or get_configured_remote_url()
        token = options['token'] or get_configured_sync_token()
        interval = max(options['interval'], 60)
        retry = max(options['retry'], 15)
        debounce = max(options['debounce'], 2)
        runs = 0
        next_due_at = 0

        if remote_url:
            remote_url = normalize_remote_url(remote_url)

        self.stdout.write('Sincronizacion periodica preparada.')

        while True:
            if not is_remote_sync_enabled():
                if options['once']:
                    self.stdout.write('Sincronizacion remota pausada desde la tienda.')
                    break
                self.stdout.write('Sincronizacion remota pausada desde la tienda. Revisando de nuevo en {}s.'.format(interval))
                self.sleep(interval)
                continue

            remote_url = remote_url or get_configured_remote_url()
            token = token or get_configured_sync_token()
            if not remote_url:
                raise CommandError('Debe configurar SYNC_REMOTE_URL o pasar --remote.')
            if not token:
                raise CommandError('Debe configurar SYNC_API_TOKEN o pasar --token.')

            pending_count = SyncOutbox.objects.filter(
                processed_at__isnull=True,
                model_label__in=get_outgoing_model_labels_for_current_node(),
            ).count()
            interval_due = time.monotonic() >= next_due_at
            if not pending_count and not interval_due:
                wait_seconds = min(debounce, max(1, int(next_due_at - time.monotonic())))
                self.sleep(wait_seconds)
                continue

            if pending_count:
                self.stdout.write('Cambios locales pendientes: {}. Sincronizando.'.format(pending_count))

            if not self.remote_available(remote_url, token, options['connectivity_timeout']):
                if options['once']:
                    raise CommandError('Render no esta disponible para sincronizar.')
                self.stdout.write(self.style.WARNING(
                    'Render no esta disponible. Reintentando en {}s.'.format(retry)
                ))
                self.sleep(retry)
                continue

            try:
                call_command(
                    'sync_with_remote',
                    remote=remote_url,
                    token=token,
                    timeout=options['timeout'],
                    limit=options['limit'],
                    pull_limit=options['pull_limit'],
                    lock_ttl=options['lock_ttl'],
                    verbosity=options.get('verbosity', 1),
                )
                runs += 1
                next_due_at = time.monotonic() + interval
            except Exception as exc:
                self.stdout.write(self.style.ERROR(
                    'Sincronizacion fallo: {}. Reintentando en {}s.'.format(exc, retry)
                ))
                if options['once']:
                    raise
                self.sleep(retry)
                continue

            if options['once']:
                break
            if options['max_runs'] and runs >= options['max_runs']:
                break

            self.stdout.write('Proxima sincronizacion en {}s.'.format(interval))
            self.sleep(debounce)

    def remote_available(self, remote_url, token, timeout):
        try:
            response = requests.get(
                urljoin(remote_url, 'sync/status/'),
                headers={'X-Sync-Token': token},
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get('sync_enabled') is False:
                self.stdout.write(self.style.WARNING('Render tiene la sincronizacion pausada desde tienda.'))
                return False
            return True
        except (ValueError, requests.RequestException) as exc:
            self.stdout.write(self.style.WARNING('Chequeo de conexion fallo: {}'.format(exc)))
            return False

    def sleep(self, seconds):
        try:
            time.sleep(seconds)
        except KeyboardInterrupt:
            raise CommandError('Sincronizacion periodica detenida por el usuario.')
