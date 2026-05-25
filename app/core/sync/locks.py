import socket
import uuid
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from app.core.sync.models import SyncRunLock


class SyncLockError(Exception):
    pass


def acquire_sync_lock(name='default', ttl_seconds=900, force=False):
    now = timezone.now()
    owner = '{}:{}'.format(socket.gethostname(), uuid.uuid4().hex[:12])

    with transaction.atomic():
        lock, _ = SyncRunLock.objects.select_for_update().get_or_create(name=name)
        if not force and lock.locked_until and lock.locked_until > now:
            raise SyncLockError(
                'Ya hay una sincronizacion activa hasta {}.'.format(lock.locked_until.isoformat())
            )

        lock.owner = owner
        lock.locked_until = now + timedelta(seconds=ttl_seconds)
        lock.save(update_fields=['owner', 'locked_until', 'updated_at'])

    return owner


def release_sync_lock(owner, name='default'):
    SyncRunLock.objects.filter(name=name, owner=owner).update(
        owner='',
        locked_until=None,
    )
