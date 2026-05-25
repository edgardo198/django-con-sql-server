from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import m2m_changed, post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from app.core.sync.context import is_sync_suppressed
from app.core.sync.models import SyncIdentity, SyncOutbox, SyncTombstone
from app.core.sync.notifier import notify_sync_required
from app.core.sync.registry import get_model_label, is_sync_model


def get_or_create_identity(instance):
    model_label = get_model_label(type(instance))
    identity, _ = SyncIdentity.objects.get_or_create(
        model_label=model_label,
        object_id=instance.pk,
    )
    return identity


def queue_instance(instance):
    if is_sync_suppressed() or not is_sync_model(type(instance)) or not instance.pk:
        return

    identity = get_or_create_identity(instance)
    SyncOutbox.objects.create(
        model_label=identity.model_label,
        object_id=identity.object_id,
        sync_uuid=identity.sync_uuid,
        action=SyncOutbox.ACTION_UPSERT,
    )
    transaction.on_commit(lambda: notify_sync_required(
        reason='local_change',
        model=identity.model_label,
        sync_uuid=identity.sync_uuid,
    ))


@receiver(post_save)
def queue_saved_instance(sender, instance, **kwargs):
    queue_instance(instance)


@receiver(pre_delete)
def queue_deleted_instance(sender, instance, **kwargs):
    if is_sync_suppressed() or not is_sync_model(sender) or not instance.pk:
        return

    identity = get_or_create_identity(instance)
    deleted_at = timezone.now()
    SyncTombstone.objects.update_or_create(
        model_label=identity.model_label,
        sync_uuid=identity.sync_uuid,
        defaults={'deleted_at': deleted_at},
    )
    SyncOutbox.objects.create(
        model_label=identity.model_label,
        object_id=identity.object_id,
        sync_uuid=identity.sync_uuid,
        action=SyncOutbox.ACTION_DELETE,
    )
    transaction.on_commit(lambda: notify_sync_required(
        reason='local_delete',
        model=identity.model_label,
        sync_uuid=identity.sync_uuid,
    ))


@receiver(m2m_changed, sender=get_user_model().groups.through)
@receiver(m2m_changed, sender=get_user_model().organizations.through)
def queue_user_m2m_change(sender, instance, action, **kwargs):
    if action in ('post_add', 'post_remove', 'post_clear'):
        queue_instance(instance)
