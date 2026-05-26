import json
import os
from hmac import compare_digest

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.management import call_command
from django.core.management.base import CommandError
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from app.core.sync.models import SyncConflict, SyncOutbox, SyncRunLock, SyncState
from app.core.sync.notifier import notify_sync_required
from app.core.sync.serializers import apply_records, collect_pull_records
from app.core.sync.registry import (
    NODE_ROLE_CENTRAL,
    SYNC_MODEL_GROUPS,
    get_incoming_model_labels_for_current_node,
    get_outgoing_model_labels_for_current_node,
    get_sync_node_role,
)
from app.core.sync.services import (
    default_remote_sync_enabled,
    get_configured_remote_url,
    get_configured_sync_token,
    is_remote_sync_enabled,
    set_remote_sync_enabled,
    update_sync_connection,
)


def get_configured_token():
    return get_configured_sync_token()


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
    outgoing_labels = get_outgoing_model_labels_for_current_node()
    return JsonResponse({
        'ok': True,
        'server_time': timezone.now().isoformat(),
        'node_role': get_sync_node_role(),
        'sync_enabled': is_remote_sync_enabled(),
        'outgoing_models': outgoing_labels,
        'incoming_models': get_incoming_model_labels_for_current_node(),
        'pending_outbox': SyncOutbox.objects.filter(
            processed_at__isnull=True,
            model_label__in=outgoing_labels,
        ).count(),
        'failed_outbox': SyncOutbox.objects.filter(
            processed_at__isnull=True,
            model_label__in=outgoing_labels,
        ).exclude(error='').count(),
        'unresolved_conflicts': SyncConflict.objects.filter(resolved=False).count(),
    })


@require_GET
def sync_pull(request):
    ok, response = require_sync_token(request)
    if not ok:
        return response
    if not is_remote_sync_enabled():
        return JsonResponse({'error': 'Sincronizacion remota desactivada desde la tienda.'}, status=503)

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
    if not is_remote_sync_enabled():
        return JsonResponse({'error': 'Sincronizacion remota desactivada desde la tienda.'}, status=503)

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


class SyncStatusPanelView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'sync/status.html'
    success_url = reverse_lazy('sync:panel')

    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        outgoing_labels = get_outgoing_model_labels_for_current_node()
        incoming_labels = get_incoming_model_labels_for_current_node()
        pending_queryset = SyncOutbox.objects.filter(
            processed_at__isnull=True,
            model_label__in=outgoing_labels,
        )
        failed_queryset = pending_queryset.exclude(error='')
        role = get_sync_node_role()
        remote_sync_enabled = is_remote_sync_enabled()
        remote_url = get_configured_remote_url()

        context.update({
            'title': 'Estado de sincronizacion',
            'node_role': role,
            'node_role_label': 'Render central' if role == NODE_ROLE_CENTRAL else 'Caja local',
            'remote_url': remote_url,
            'token_configured': bool(get_configured_token()),
            'cloud_backup_enabled': default_remote_sync_enabled(),
            'remote_sync_enabled': remote_sync_enabled,
            'remote_sync_status_label': 'Activo' if remote_sync_enabled else 'Pausado',
            'remote_sync_toggle_label': (
                'Desactivar sincronizacion' if remote_sync_enabled else 'Activar sincronizacion'
            ),
            'remote_sync_toggle_value': '0' if remote_sync_enabled else '1',
            'interval_seconds': max(env_int('SYNC_INTERVAL_SECONDS', 300), 60),
            'retry_seconds': max(env_int('SYNC_RETRY_SECONDS', 30), 15),
            'pending_count': pending_queryset.count(),
            'failed_count': failed_queryset.count(),
            'recent_pending': pending_queryset.order_by('-created_at')[:8],
            'states': SyncState.objects.order_by('-updated_at')[:5],
            'active_lock': SyncRunLock.objects.filter(locked_until__gt=timezone.now()).first(),
            'unresolved_conflict_count': SyncConflict.objects.filter(resolved=False).count(),
            'unresolved_conflicts': SyncConflict.objects.filter(resolved=False).order_by('-created_at')[:8],
            'outgoing_models': outgoing_labels,
            'incoming_models': incoming_labels,
            'model_groups': SYNC_MODEL_GROUPS,
            'panel_url': reverse_lazy('sync:panel'),
        })
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')

        if action == 'toggle_sync':
            enabled = request.POST.get('enabled') == '1'
            set_remote_sync_enabled(enabled, request.user)
            messages.success(
                request,
                'Sincronizacion remota {} desde la tienda.'.format('activada' if enabled else 'pausada'),
            )
            return redirect(self.success_url)

        if action == 'save_connection':
            remote_url = (request.POST.get('remote_url') or '').strip()
            sync_token = (request.POST.get('sync_token') or '').strip()
            if not remote_url:
                messages.error(request, 'Ingrese la URL de Render antes de guardar.')
                return redirect(self.success_url)
            if not sync_token and not get_configured_token():
                messages.error(request, 'Ingrese el token de sincronizacion antes de guardar.')
                return redirect(self.success_url)
            update_sync_connection(remote_url, sync_token, request.user)
            messages.success(request, 'Conexion de Render guardada correctamente.')
            return redirect(self.success_url)

        if action != 'sync_now':
            messages.error(request, 'Accion de sincronizacion no reconocida.')
            return redirect(self.success_url)

        if not is_remote_sync_enabled():
            messages.warning(request, 'La sincronizacion remota esta pausada. Activala antes de sincronizar.')
            return redirect(self.success_url)

        remote_url = get_configured_remote_url()
        token = get_configured_token()
        if not remote_url or not token:
            messages.error(request, 'Configure SYNC_REMOTE_URL y SYNC_API_TOKEN antes de sincronizar.')
            return redirect(self.success_url)

        try:
            call_command('sync_with_remote', remote=remote_url, token=token, verbosity=0)
        except CommandError as exc:
            messages.error(request, 'No se pudo sincronizar: {}'.format(exc))
        except Exception as exc:
            messages.error(request, 'Sincronizacion fallida: {}'.format(exc))
        else:
            messages.success(request, 'Sincronizacion ejecutada correctamente.')
        return redirect(self.success_url)
