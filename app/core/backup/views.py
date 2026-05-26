from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View

from app.core.backup.services import (
    BackupError,
    create_local_backup,
    delete_local_backup,
    list_local_backups,
    resolve_backup_dir,
    restore_local_backup,
    safe_backup_path,
)


class BackupAdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


class LocalBackupView(BackupAdminRequiredMixin, View):
    template_name = 'backup/local.html'
    success_url = reverse_lazy('backup:local')

    def get_context_data(self):
        backups = list_local_backups()
        return {
            'title': 'Respaldos locales',
            'entity': 'Respaldos',
            'list_url': self.success_url,
            'backups': backups,
            'backup_dir': resolve_backup_dir(),
            'latest_backup': backups[0] if backups else None,
            'total_backups': len(backups),
        }

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')

        try:
            if action == 'create':
                result = create_local_backup(
                    label=request.POST.get('label', ''),
                    keep=request.POST.get('keep') or None,
                    include_media=request.POST.get('include_media') == 'on',
                )
                messages.success(request, 'Respaldo creado: {}'.format(result['filename']))
                if result['removed']:
                    messages.info(request, 'Respaldos antiguos eliminados: {}'.format(result['removed']))
            elif action == 'delete':
                deleted_path = delete_local_backup(request.POST.get('filename', ''))
                messages.success(request, 'Respaldo eliminado: {}'.format(deleted_path.name))
            elif action == 'restore':
                confirmation = (request.POST.get('confirmation') or '').strip()
                if confirmation != 'RESTAURAR':
                    raise BackupError('Escribe RESTAURAR para confirmar la restauracion.')
                result = restore_local_backup(
                    request.POST.get('filename', ''),
                    restore_media=request.POST.get('restore_media') == 'on',
                    confirmed=True,
                    verbosity=0,
                )
                messages.success(request, 'Respaldo restaurado: {}'.format(result['filename']))
            else:
                raise BackupError('Accion no valida.')
        except (BackupError, ValueError) as exc:
            messages.error(request, str(exc))

        return redirect(self.success_url)


class LocalBackupDownloadView(BackupAdminRequiredMixin, View):
    def get(self, request, filename, *args, **kwargs):
        try:
            backup_path = safe_backup_path(filename)
        except BackupError as exc:
            raise Http404(str(exc))

        return FileResponse(
            backup_path.open('rb'),
            as_attachment=True,
            filename=backup_path.name,
            content_type='application/zip',
        )
