from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from app.core.sync.consumers import SYNC_GROUP


def notify_sync_required(reason='remote_change', model='', sync_uuid=''):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    async_to_sync(channel_layer.group_send)(
        SYNC_GROUP,
        {
            'type': 'sync.required',
            'reason': reason,
            'model': model,
            'sync_uuid': str(sync_uuid or ''),
        },
    )
