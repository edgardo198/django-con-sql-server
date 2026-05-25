import os
from urllib.parse import urljoin

import requests
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from app.core.sync.locks import SyncLockError, acquire_sync_lock, release_sync_lock
from app.core.sync.models import SyncState
from app.core.sync.serializers import (
    apply_records,
    get_pending_outbox,
    mark_outbox_failed,
    mark_outbox_processed,
    serialize_outbox_item,
)


def normalize_remote_url(remote_url):
    return remote_url.rstrip('/') + '/'


def parse_server_time(value):
    parsed = parse_datetime(value or '')
    if parsed and timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed or timezone.now()


class Command(BaseCommand):
    help = 'Sincroniza la base local con un servidor remoto Render/Django.'

    def add_arguments(self, parser):
        parser.add_argument('--remote', default=os.getenv('SYNC_REMOTE_URL'))
        parser.add_argument('--token', default=os.getenv('SYNC_API_TOKEN') or os.getenv('DJANGO_SYNC_TOKEN'))
        parser.add_argument('--timeout', type=int, default=int(os.getenv('SYNC_TIMEOUT', '30')))
        parser.add_argument('--limit', type=int, default=int(os.getenv('SYNC_BATCH_SIZE', '250')))
        parser.add_argument('--pull-limit', type=int, default=int(os.getenv('SYNC_PULL_BATCH_SIZE', '500')))
        parser.add_argument('--lock-ttl', type=int, default=int(os.getenv('SYNC_LOCK_TTL_SECONDS', '900')))
        parser.add_argument('--force-lock', action='store_true')
        parser.add_argument('--pull-only', action='store_true')
        parser.add_argument('--push-only', action='store_true')

    def handle(self, *args, **options):
        remote_url = options['remote']
        token = options['token']
        timeout = options['timeout']
        limit = options['limit']
        pull_limit = options['pull_limit']

        if not remote_url:
            raise CommandError('Debe configurar SYNC_REMOTE_URL o pasar --remote.')
        if not token:
            raise CommandError('Debe configurar SYNC_API_TOKEN o pasar --token.')

        remote_url = normalize_remote_url(remote_url)
        try:
            lock_owner = acquire_sync_lock(
                ttl_seconds=options['lock_ttl'],
                force=options['force_lock'],
            )
        except SyncLockError as exc:
            raise CommandError(str(exc))

        try:
            state, _ = SyncState.objects.get_or_create(remote_url=remote_url)
            session = requests.Session()
            session.headers.update({'X-Sync-Token': token})

            pulled = 0
            pushed = 0

            try:
                if not options['push_only']:
                    pulled = self.pull(session, remote_url, state, timeout, pull_limit)

                if not options['pull_only']:
                    pushed = self.push(session, remote_url, state, timeout, limit)

                if pushed and not options['push_only']:
                    pulled += self.pull(session, remote_url, state, timeout, pull_limit)

                state.last_error = ''
                state.save(update_fields=['last_error', 'updated_at'])
            except Exception as exc:
                state.last_error = str(exc)
                state.save(update_fields=['last_error', 'updated_at'])
                raise

            self.stdout.write(self.style.SUCCESS('Sincronizacion completada. pull={} push={}'.format(pulled, pushed)))
        finally:
            release_sync_lock(lock_owner)

    def pull(self, session, remote_url, state, timeout, pull_limit):
        params = {}
        if state.last_pull_at:
            params['since'] = state.last_pull_at.isoformat()

        offset = 0
        count = 0
        final_server_time = None
        while True:
            page_params = dict(params)
            page_params['offset'] = offset
            page_params['limit'] = pull_limit
            response = session.get(urljoin(remote_url, 'sync/pull/'), params=page_params, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
            final_server_time = final_server_time or parse_server_time(payload.get('server_time'))

            results = apply_records(payload.get('records') or [])
            for result in results:
                if result.get('status') in ('applied', 'deleted', 'conflict'):
                    count += 1

            if not payload.get('has_more'):
                break
            offset += payload.get('limit') or pull_limit

        state.last_pull_at = final_server_time or timezone.now()
        state.save(update_fields=['last_pull_at', 'updated_at'])
        return count

    def push(self, session, remote_url, state, timeout, limit):
        pending = get_pending_outbox(limit=limit)
        if not pending:
            return 0

        records = []
        sent_items = []
        for item in pending:
            record = serialize_outbox_item(item)
            if record is None:
                item.error = 'No se pudo serializar el registro.'
                item.save(update_fields=['error'])
                continue
            records.append(record)
            sent_items.append(item)

        if not records:
            return 0

        try:
            response = session.post(
                urljoin(remote_url, 'sync/push/'),
                json={'records': records},
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get('accepted') != len(records):
                raise CommandError('El servidor no acepto todos los registros enviados.')

            deferred = [
                result for result in payload.get('results', [])
                if result.get('status') == 'deferred'
            ]
            if deferred:
                raise CommandError('El servidor aplazo {} registros por dependencias pendientes.'.format(len(deferred)))
        except Exception as exc:
            mark_outbox_failed(sent_items, exc)
            raise

        mark_outbox_processed(sent_items)
        state.last_push_at = parse_server_time(payload.get('server_time'))
        state.save(update_fields=['last_push_at', 'updated_at'])
        return len(records)
