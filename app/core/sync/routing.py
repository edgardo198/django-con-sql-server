from django.urls import re_path

from app.core.sync.consumers import SyncConsumer


websocket_urlpatterns = [
    re_path(r'^ws/sync/$', SyncConsumer.as_asgi()),
]
