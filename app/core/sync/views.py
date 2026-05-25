import json
import os
from hmac import compare_digest

from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from app.core.sync.notifier import notify_sync_required
from app.core.sync.serializers import apply_records, collect_pull_records


def get_configured_token():
    return os.getenv('SYNC_API_TOKEN') or os.getenv('DJANGO_SYNC_TOKEN') or ''


def request_token(request):
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header.split(' ', 1)[1].strip()
    return request.headers.get('X-Sync-Token', '').strip()


def require_sync_token(request):
    configured_token = get_configured_token()
    if not configured_token:
        return False, JsonResponse(
            {'error': 'SYNC_API_TOKEN no esta configurado en este servidor.'},
            status=503,
        )

    token = request_token(request)
    if not token or not compare_digest(token, configured_token):
        return False, JsonResponse({'error': 'Token de sincronizacion invalido.'}, status=403)

    return True, None


def parse_since(value):
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed and timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def bounded_int(value, default, minimum, maximum):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(parsed, maximum))


@require_GET
def sync_status(request):
    ok, response = require_sync_token(request)
    if not ok:
        return response
    return JsonResponse({'ok': True, 'server_time': timezone.now().isoformat()})


@require_GET
def sync_pull(request):
    ok, response = require_sync_token(request)
    if not ok:
        return response

    since = parse_since(request.GET.get('since'))
    max_limit = env_int('SYNC_PULL_LIMIT_MAX', 1000)
    default_limit = env_int('SYNC_PULL_LIMIT', 500)
    limit = bounded_int(request.GET.get('limit'), default_limit, 1, max_limit)
    offset = bounded_int(request.GET.get('offset'), 0, 0, 10**9)
    server_time = timezone.now()
    records, total, has_more = collect_pull_records(since=since, offset=offset, limit=limit)
    return JsonResponse({
        'server_time': server_time.isoformat(),
        'records': records,
        'total': total,
        'offset': offset,
        'limit': limit,
        'has_more': has_more,
    })


@csrf_exempt
@require_POST
def sync_push(request):
    ok, response = require_sync_token(request)
    if not ok:
        return response

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        return JsonResponse({'error': 'JSON invalido.'}, status=400)

    records = payload.get('records') or []
    if not isinstance(records, list):
        return JsonResponse({'error': 'records debe ser una lista.'}, status=400)

    max_records = env_int('SYNC_PUSH_LIMIT_MAX', 500)
    if len(records) > max_records:
        return JsonResponse(
            {'error': 'Demasiados registros en un push. Maximo: {}'.format(max_records)},
            status=413,
        )

    try:
        results = apply_records(records)
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    notify_sync_required(reason='remote_push')

    return JsonResponse({
        'server_time': timezone.now().isoformat(),
        'accepted': len(records),
        'results': results,
    })
