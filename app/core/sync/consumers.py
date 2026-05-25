import json
import os
from hmac import compare_digest
from urllib.parse import parse_qs

from channels.generic.websocket import AsyncWebsocketConsumer


SYNC_GROUP = 'sync_clients'


def configured_token():
    return os.getenv('SYNC_API_TOKEN') or os.getenv('DJANGO_SYNC_TOKEN') or ''


class SyncConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        token = self.request_token()
        expected = configured_token()
        if not expected or not token or not compare_digest(token, expected):
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(SYNC_GROUP, self.channel_name)
        await self.accept()
        await self.send_json({
            'type': 'sync_connected',
        })

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(SYNC_GROUP, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            try:
                payload = json.loads(text_data)
            except ValueError:
                return
            if payload.get('type') == 'ping':
                await self.send_json({'type': 'pong'})

    async def sync_required(self, event):
        await self.send_json({
            'type': 'sync_required',
            'reason': event.get('reason', 'remote_change'),
            'model': event.get('model', ''),
            'sync_uuid': event.get('sync_uuid', ''),
        })

    def request_token(self):
        headers = {
            key.decode('latin1').lower(): value.decode('latin1')
            for key, value in self.scope.get('headers', [])
        }
        auth_header = headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header.split(' ', 1)[1].strip()
        header_token = headers.get('x-sync-token', '').strip()
        if header_token:
            return header_token

        query_string = self.scope.get('query_string', b'').decode('utf-8')
        values = parse_qs(query_string)
        return (values.get('token') or [''])[0]

    async def send_json(self, payload):
        await self.send(text_data=json.dumps(payload))
