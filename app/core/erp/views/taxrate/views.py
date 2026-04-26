from django.urls import reverse_lazy
from django.utils.safestring import mark_safe

from app.core.erp.forms import TaxRateForm
from app.core.erp.models import TaxRate
from app.core.erp.views.base import ERPAjaxCreateView, ERPAjaxDeleteView, ERPAjaxUpdateView, ERPTableListView


def render_boolean_badge(value, true_label='Si', false_label='No'):
    css_class = 'badge-success' if value else 'badge-secondary'
    label = true_label if value else false_label
    return mark_safe(f'<span class="badge {css_class}">{label}</span>')


class TaxRateListView(ERPTableListView):
    model = TaxRate
    permission_required = 'erp.view_taxrate'
    title = 'Listado de Tasas de Impuesto'
    entity = 'Tasas de impuesto'
    create_url_name = 'erp:taxrate_create'
    update_url_name = 'erp:taxrate_update'
    delete_url_name = 'erp:taxrate_delete'
    can_create_permission = 'erp.add_taxrate'
    can_change_permission = 'erp.change_taxrate'
    can_delete_permission = 'erp.delete_taxrate'

    def get_queryset(self):
        return super().get_queryset().order_by('name')

    def get_table_columns(self):
        return ['Nro', 'Nombre', 'Codigo', 'Porcentaje', 'Predeterminado', 'Estado']

    def get_row_cells(self, obj):
        return [
            obj.id,
            obj.name,
            obj.code,
            f'{obj.rate:.2f}%',
            render_boolean_badge(obj.is_default, 'Si', 'No'),
            render_boolean_badge(obj.is_active, 'Activo', 'Inactivo'),
        ]


class TaxRateCreateView(ERPAjaxCreateView):
    model = TaxRate
    form_class = TaxRateForm
    template_name = 'form.html'
    success_url = reverse_lazy('erp:taxrate_list')
    permission_required = 'erp.add_taxrate'
    url_redirect = success_url
    title = 'Creacion de una Tasa de Impuesto'
    entity = 'Tasas de impuesto'


class TaxRateUpdateView(ERPAjaxUpdateView):
    model = TaxRate
    form_class = TaxRateForm
    template_name = 'form.html'
    success_url = reverse_lazy('erp:taxrate_list')
    permission_required = 'erp.change_taxrate'
    url_redirect = success_url
    title = 'Edicion de una Tasa de Impuesto'
    entity = 'Tasas de impuesto'


class TaxRateDeleteView(ERPAjaxDeleteView):
    model = TaxRate
    template_name = 'delete.html'
    success_url = reverse_lazy('erp:taxrate_list')
    permission_required = 'erp.delete_taxrate'
    url_redirect = success_url
    title = 'Eliminacion de una Tasa de Impuesto'
    entity = 'Tasas de impuesto'
