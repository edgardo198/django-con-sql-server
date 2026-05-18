import os
import logging
from io import BytesIO
from urllib.parse import urlparse

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils import timezone


logger = logging.getLogger(__name__)


class DatabaseMediaStorage(Storage):
    def _normalize_name(self, name):
        normalized = os.path.normpath(str(name)).replace('\\', '/').lstrip('/')
        media_path = urlparse(settings.MEDIA_URL).path.strip('/')
        prefixes = [prefix for prefix in (media_path, 'media') if prefix]
        for prefix in prefixes:
            if normalized == prefix:
                return ''
            if normalized.startswith('{}/'.format(prefix)):
                normalized = normalized[len(prefix) + 1:]
                break
        return normalized

    def _open(self, name, mode='rb'):
        from app.core.user.models import StoredMediaFile

        stored_file = StoredMediaFile.objects.get(name=self._normalize_name(name))
        file_obj = ContentFile(bytes(stored_file.content), name=stored_file.name)
        file_obj.file = BytesIO(bytes(stored_file.content))
        return file_obj

    def _save(self, name, content):
        from app.core.user.models import StoredMediaFile

        normalized_name = self._normalize_name(name)
        if not normalized_name:
            raise ValueError('El nombre del archivo media no es valido.')
        if hasattr(content, 'seek'):
            content.seek(0)
        data = b''.join(chunk for chunk in content.chunks())
        content_type = getattr(content, 'content_type', '') or ''

        StoredMediaFile.objects.update_or_create(
            name=normalized_name,
            defaults={
                'content': data,
                'content_type': content_type,
                'size': len(data),
            },
        )
        logger.warning(
            'Media guardado en PostgreSQL: name=%s size=%s content_type=%s',
            normalized_name,
            len(data),
            content_type,
        )
        return normalized_name

    def delete(self, name):
        from app.core.user.models import StoredMediaFile

        StoredMediaFile.objects.filter(name=self._normalize_name(name)).delete()

    def exists(self, name):
        from app.core.user.models import StoredMediaFile

        return StoredMediaFile.objects.filter(name=self._normalize_name(name)).exists()

    def size(self, name):
        from app.core.user.models import StoredMediaFile

        return StoredMediaFile.objects.get(name=self._normalize_name(name)).size

    def url(self, name):
        from django.conf import settings

        return '{}{}'.format(settings.MEDIA_URL, self._normalize_name(name))

    def get_modified_time(self, name):
        from app.core.user.models import StoredMediaFile

        return StoredMediaFile.objects.get(name=self._normalize_name(name)).updated_at

    def get_created_time(self, name):
        from app.core.user.models import StoredMediaFile

        return StoredMediaFile.objects.get(name=self._normalize_name(name)).created_at

    def get_accessed_time(self, name):
        return timezone.now()
