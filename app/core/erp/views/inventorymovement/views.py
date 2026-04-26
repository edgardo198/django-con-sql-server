from app.core.erp.models import InventoryMovement
from app.core.erp.views.base import ERPTableListView


class InventoryMovementListView(ERPTableListView):
    model = InventoryMovement
    permission_required = 'erp.view_inventorymovement'
    title = 'Listado de Movimientos de Inventario'
    entity = 'Movimientos de inventario'
    show_actions = False

    def get_queryset(self):
        return super().get_queryset().select_related('product').order_by('-date_joined', '-id')

    def get_table_columns(self):
        return ['Nro', 'Producto', 'Tipo', 'Cantidad', 'Stock anterior', 'Stock actual', 'Referencia', 'Fecha']

    def get_row_cells(self, obj):
        return [
            obj.id,
            obj.product.name,
            obj.get_movement_type_display(),
            obj.quantity,
            obj.stock_before,
            obj.stock_after,
            obj.reference or '-',
            obj.date_joined.strftime('%Y-%m-%d %H:%M'),
        ]
