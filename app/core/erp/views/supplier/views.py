from django.urls import reverse_lazy
from django.utils.safestring import mark_safe

from app.core.erp.forms import SupplierForm
from app.core.erp.models import Supplier
from app.core.erp.views.base import ERPAjaxCreateView, ERPAjaxDeleteView, ERPAjaxUpdateView, ERPTableListView


def render_active_badge(value):
    css_class = 'badge-success' if value else 'badge-secondary'
    label = 'Activo' if value else 'Inactivo'
    return mark_safe(f'<span class="badge {css_class}">{label}</span>')


class SupplierListView(ERPTableListView):
    model = Supplier
    permission_required = 'erp.view_supplier'
    title = 'Listado de Proveedores'
    entity = 'Proveedores'
    create_url_name = 'erp:supplier_create'
    update_url_name = 'erp:supplier_update'
    delete_url_name = 'erp:supplier_delete'
    can_create_permission = 'erp.add_supplier'
    can_change_permission = 'erp.change_supplier'
    can_delete_permission = 'erp.delete_supplier'

    def get_queryset(self):
        return super().get_queryset().order_by('name')

    def get_table_columns(self):
        return ['Nro', 'Proveedor', 'Contacto', 'Telefono', 'Correo', 'Estado']

    def get_row_cells(self, obj):
        return [
            obj.id,
            obj.name,
            obj.contact_name or '-',
            obj.phone or '-',
            obj.email or '-',
            render_active_badge(obj.is_active),
        ]


class SupplierCreateView(ERPAjaxCreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'form.html'
    success_url = reverse_lazy('erp:supplier_list')
    permission_required = 'erp.add_supplier'
    url_redirect = success_url
    title = 'Creacion de un Proveedor'
    entity = 'Proveedores'


class SupplierUpdateView(ERPAjaxUpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'form.html'
    success_url = reverse_lazy('erp:supplier_list')
    permission_required = 'erp.change_supplier'
    url_redirect = success_url
    title = 'Edicion de un Proveedor'
    entity = 'Proveedores'


class SupplierDeleteView(ERPAjaxDeleteView):
    model = Supplier
    template_name = 'delete.html'
    success_url = reverse_lazy('erp:supplier_list')
    permission_required = 'erp.delete_supplier'
    url_redirect = success_url
    title = 'Eliminacion de un Proveedor'
    entity = 'Proveedores'
