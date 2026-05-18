import mimetypes
import os
from pathlib import PurePosixPath
from urllib.parse import urlparse

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders
from django.db.utils import OperationalError, ProgrammingError
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.views.decorators.http import require_GET


def _content_type_for_file(file_path, default='application/octet-stream'):
    try:
        from PIL import Image

        with Image.open(file_path) as image:
            return Image.MIME.get(image.format, default)
    except Exception:
        return mimetypes.guess_type(file_path)[0] or default


def _safe_media_path(path):
    cleaned = str(PurePosixPath(str(path).replace('\\', '/'))).lstrip('/')
    parts = PurePosixPath(cleaned).parts
    if not cleaned or '..' in parts:
        raise Http404('Archivo no encontrado')
    return cleaned


def _candidate_media_paths(path):
    candidates = []
    media_prefix = urlparse(settings.MEDIA_URL).path.strip('/')
    prefixes = [prefix for prefix in (media_prefix, 'media') if prefix]

    for candidate in (path,):
        candidate = str(PurePosixPath(candidate)).lstrip('/')
        if candidate and candidate not in candidates:
            candidates.append(candidate)
        for prefix in prefixes:
            if candidate.startswith('{}/'.format(prefix)):
                stripped = candidate[len(prefix) + 1:]
                if stripped and stripped not in candidates:
                    candidates.append(stripped)
    return candidates


def _fallback_image_response(path):
    content_type, _ = mimetypes.guess_type(path)
    if content_type and content_type.startswith('image/'):
        fallback_path = finders.find('img/imagen.png')
        if fallback_path and os.path.exists(fallback_path):
            return FileResponse(open(fallback_path, 'rb'), content_type=_content_type_for_file(fallback_path))
    raise Http404('Archivo no encontrado')


@require_GET
def serve_media(request, path):
    safe_path = _safe_media_path(path)
    candidate_paths = _candidate_media_paths(safe_path)

    try:
        from app.core.user.models import StoredMediaFile

        stored_file = StoredMediaFile.objects.filter(name__in=candidate_paths).first()
    except (OperationalError, ProgrammingError):
        stored_file = None

    if stored_file is not None:
        content_type = stored_file.content_type or mimetypes.guess_type(safe_path)[0]
        response = HttpResponse(bytes(stored_file.content), content_type=content_type or 'application/octet-stream')
        response['Content-Length'] = stored_file.size
        response['Cache-Control'] = 'no-store, max-age=0'
        return response

    filesystem_storage = FileSystemStorage(location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL)
    for candidate_path in candidate_paths:
        for storage in (default_storage, filesystem_storage):
            try:
                if storage.exists(candidate_path):
                    content_type, encoding = mimetypes.guess_type(candidate_path)
                    response = FileResponse(
                        storage.open(candidate_path, 'rb'),
                        content_type=content_type or 'application/octet-stream',
                    )
                    if encoding:
                        response['Content-Encoding'] = encoding
                    response['Cache-Control'] = 'no-store, max-age=0'
                    return response
            except (OperationalError, ProgrammingError, OSError, ValueError):
                continue

    return _fallback_image_response(safe_path)


@login_required
@require_GET
def media_diagnostics_view(request):
    if not request.user.is_staff and not request.user.is_superuser:
        raise Http404('Archivo no encontrado')

    from django.core.files.storage import default_storage

    diagnostics = {
        'debug': settings.DEBUG,
        'media_url': settings.MEDIA_URL,
        'media_root': settings.MEDIA_ROOT,
        'serve_media': getattr(settings, 'SERVE_MEDIA', None),
        'use_database_media_storage': getattr(settings, 'USE_DATABASE_MEDIA_STORAGE', None),
        'default_storage_class': '{}.{}'.format(
            default_storage.__class__.__module__,
            default_storage.__class__.__name__,
        ),
        'latest_products': [],
        'stored_media': {},
    }

    try:
        from app.core.user.models import StoredMediaFile

        latest_files = StoredMediaFile.objects.order_by('-updated_at')[:10]
        diagnostics['stored_media'] = {
            'count': StoredMediaFile.objects.count(),
            'latest': [
                {
                    'name': item.name,
                    'url': '{}{}'.format(settings.MEDIA_URL, item.name),
                    'size': item.size,
                    'content_type': item.content_type,
                }
                for item in latest_files
            ],
        }
    except (OperationalError, ProgrammingError):
        diagnostics['stored_media'] = {'error': 'La tabla StoredMediaFile no existe o no esta disponible.'}

    try:
        from app.core.erp.models import Product

        products = Product.objects.exclude(image='').order_by('-id')[:10]
        diagnostics['latest_products'] = [
            {
                'id': product.id,
                'name': product.name,
                'image': product.image.name,
                'url': product.image.url if product.image else '',
                'storage_exists': default_storage.exists(product.image.name) if product.image else False,
                'candidate_paths': _candidate_media_paths(product.image.name) if product.image else [],
            }
            for product in products
        ]
    except (OperationalError, ProgrammingError):
        diagnostics['latest_products'] = [{'error': 'La tabla de productos no esta disponible.'}]

    return JsonResponse(diagnostics, json_dumps_params={'indent': 2})
