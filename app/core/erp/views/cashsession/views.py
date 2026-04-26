from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.views import View

from app.core.erp.forms import CashSessionCloseForm, CashSessionForm
from app.core.erp.mixins import CurrentOrganizationMixin, ValidatePermissionRequiredMixin
from app.core.erp.models import CashSession
from app.core.erp.views.base import ERPAjaxCreateView, ERPTableListView


def render_status_badge(status, label):
    css_class = 'badge-success' if status == 'open' else 'badge-secondary'
    return mark_safe(f'<span class="badge {css_class}">{label}</span>')


class CashSessionListView(ERPTableListView):
    model = CashSession
    permission_required = 'erp.view_cashsession'
    title = 'Listado de Cajas'
    entity = 'Cajas'
    create_url_name = 'erp:cashsession_create'
    can_create_permission = 'erp.add_cashsession'
    can_change_permission = 'erp.change_cashsession'
    show_actions = True

    def get_queryset(self):
        return super().get_queryset().select_related('user').order_by('-opened_at', '-id')

    def get_table_columns(self):
        return ['Nro', 'Usuario', 'Apertura', 'Cierre', 'Monto apertura', 'Monto esperado', 'Diferencia', 'Estado']

    def get_row_cells(self, obj):
        return [
            obj.id,
            obj.user.get_full_name() or obj.user.username,
            obj.opened_at.strftime('%Y-%m-%d %H:%M'),
            obj.closed_at.strftime('%Y-%m-%d %H:%M') if obj.closed_at else '-',
            f'L {obj.opening_amount:.2f}',
            f'L {obj.expected_amount:.2f}',
            f'L {obj.difference:.2f}',
            render_status_badge(obj.status, obj.get_status_display()),
        ]

    def get_row_actions(self, obj):
        actions = []
        if obj.status == 'open' and self.request.user.has_perm('erp.change_cashsession'):
            actions.append({
                'label': 'Cerrar',
                'icon': 'fas fa-cash-register',
                'url': reverse_lazy('erp:cashsession_close', kwargs={'pk': obj.pk}),
                'class': 'btn btn-warning btn-xs btn-flat',
            })
        return actions


class CashSessionCreateView(ERPAjaxCreateView):
    model = CashSession
    form_class = CashSessionForm
    template_name = 'form.html'
    success_url = reverse_lazy('erp:cashsession_list')
    permission_required = 'erp.add_cashsession'
    url_redirect = success_url
    title = 'Apertura de Caja'
    entity = 'Cajas'


class CashSessionCloseView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, View):
    permission_required = 'erp.change_cashsession'
    url_redirect = reverse_lazy('erp:cashsession_list')
    template_name = 'form.html'

    def get_object(self):
        return get_object_or_404(
            CashSession.objects.filter(organization=self.get_current_organization()),
            pk=self.kwargs['pk'],
        )

    def get(self, request, *args, **kwargs):
        context = {
            'form': CashSessionCloseForm(),
            'title': 'Cierre de Caja',
            'entity': 'Cajas',
            'list_url': reverse_lazy('erp:cashsession_list'),
            'action': 'close',
            'current_organization': self.get_current_organization(),
            'available_organizations': request.user.get_accessible_organizations(),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = CashSessionCloseForm(request.POST)
        if not form.is_valid():
            return JsonResponse({'error': form.errors})

        cash_session = self.get_object()
        try:
            cash_session.notes = form.cleaned_data.get('notes') or cash_session.notes
            if request.user.is_authenticated:
                cash_session.user_updated = request.user
            cash_session.close_session(form.cleaned_data['closing_amount'])
            cash_session.save(update_fields=['notes', 'user_updated'])
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)})
