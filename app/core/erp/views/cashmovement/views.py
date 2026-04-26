from django.http import JsonResponse
from django.urls import reverse_lazy

from app.core.erp.forms import CashMovementForm
from app.core.erp.models import CashMovement
from app.core.erp.views.base import ERPAjaxCreateView, ERPAjaxDeleteView, ERPTableListView


class CashMovementListView(ERPTableListView):
    model = CashMovement
    permission_required = 'erp.view_cashmovement'
    title = 'Listado de Movimientos de Caja'
    entity = 'Movimientos de caja'
    create_url_name = 'erp:cashmovement_create'
    delete_url_name = 'erp:cashmovement_delete'
    can_create_permission = 'erp.add_cashmovement'
    can_delete_permission = 'erp.delete_cashmovement'

    def get_queryset(self):
        return super().get_queryset().select_related('cash_session').order_by('-id')

    def get_table_columns(self):
        return ['Nro', 'Caja', 'Tipo', 'Monto', 'Referencia', 'Descripcion']

    def get_row_cells(self, obj):
        return [
            obj.id,
            obj.cash_session_id,
            obj.get_movement_type_display(),
            f'L {obj.amount:.2f}',
            obj.reference or '-',
            obj.description or '-',
        ]


class CashMovementCreateView(ERPAjaxCreateView):
    model = CashMovement
    form_class = CashMovementForm
    template_name = 'form.html'
    success_url = reverse_lazy('erp:cashmovement_list')
    permission_required = 'erp.add_cashmovement'
    url_redirect = success_url
    title = 'Registro de Movimiento de Caja'
    entity = 'Movimientos de caja'


class CashMovementDeleteView(ERPAjaxDeleteView):
    model = CashMovement
    template_name = 'delete.html'
    success_url = reverse_lazy('erp:cashmovement_list')
    permission_required = 'erp.delete_cashmovement'
    url_redirect = success_url
    title = 'Eliminacion de un Movimiento de Caja'
    entity = 'Movimientos de caja'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            movement = self.get_object()
            cash_session = movement.cash_session
            movement.delete()
            cash_session.recalculate()
            data['success'] = True
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)
