import json
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from app.core.erp.forms import PurchaseForm
from app.core.erp.mixins import CurrentOrganizationMixin, ValidatePermissionRequiredMixin
from app.core.erp.models import DetPurchase, Product, Purchase, Supplier, effective_tax_rate_percent
from app.core.erp.views.base import ERPAjaxDeleteView, ERPTableListView


class PurchaseListView(ERPTableListView):
    model = Purchase
    permission_required = 'erp.view_purchase'
    title = 'Listado de Compras'
    entity = 'Compras'
    create_url_name = 'erp:purchase_create'
    update_url_name = 'erp:purchase_update'
    delete_url_name = 'erp:purchase_delete'
    can_create_permission = 'erp.add_purchase'
    can_change_permission = 'erp.change_purchase'
    can_delete_permission = 'erp.delete_purchase'

    def get_queryset(self):
        return super().get_queryset().select_related('supplier').order_by('-date_joined', '-id')

    def get_table_columns(self):
        return ['Nro', 'Proveedor', 'Fecha', 'Condicion', 'Subtotal', 'ISV', 'Total', 'Saldo', 'Estado']

    def get_row_cells(self, obj):
        return [
            obj.id,
            obj.supplier.name,
            obj.date_joined.strftime('%Y-%m-%d'),
            obj.get_payment_term_display(),
            f'L {obj.subtotal:.2f}',
            f'L {obj.tax_total:.2f}',
            f'L {obj.total:.2f}',
            f'L {obj.balance:.2f}',
            obj.get_status_display(),
        ]

    def get_row_actions(self, obj):
        actions = []
        can_change = self.request.user.has_perm('erp.change_purchase')
        can_delete = self.request.user.has_perm('erp.delete_purchase')

        if obj.status == 'draft' and can_change:
            actions.append({
                'label': 'Editar',
                'icon': 'fas fa-edit',
                'url': reverse_lazy('erp:purchase_update', kwargs={'pk': obj.pk}),
                'class': 'btn btn-primary btn-xs btn-flat',
            })
            actions.append({
                'label': 'Confirmar',
                'icon': 'fas fa-check',
                'url': reverse_lazy('erp:purchase_confirm', kwargs={'pk': obj.pk}),
                'class': 'btn btn-success btn-xs btn-flat',
            })

        if obj.status == 'confirmed' and can_change:
            actions.append({
                'label': 'Anular',
                'icon': 'fas fa-ban',
                'url': reverse_lazy('erp:purchase_cancel', kwargs={'pk': obj.pk}),
                'class': 'btn btn-warning btn-xs btn-flat',
            })

        if obj.status == 'draft' and can_delete:
            actions.append({
                'label': 'Eliminar',
                'icon': 'fas fa-trash-alt',
                'url': reverse_lazy('erp:purchase_delete', kwargs={'pk': obj.pk}),
                'class': 'btn btn-danger btn-xs btn-flat',
            })

        return actions


class PurchaseBaseEditorView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, View):
    form_class = PurchaseForm
    template_name = 'purchase/create.html'
    success_url = reverse_lazy('erp:purchase_list')

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        if 'pk' not in self.kwargs:
            return None
        return get_object_or_404(
            Purchase.objects.filter(organization=self.get_current_organization()).select_related('supplier'),
            pk=self.kwargs['pk'],
        )

    def get_form(self):
        kwargs = {'request': self.request}
        obj = self.get_object()
        if obj is not None:
            kwargs['instance'] = obj
        return self.form_class(**kwargs)

    def get_product_queryset(self):
        queryset = Product.objects.filter(
            organization=self.get_current_organization()
        ).select_related('category', 'cat', 'tax_rate')
        if hasattr(Product, 'is_active'):
            queryset = queryset.filter(is_active=True)
        return queryset.order_by('name')

    def search_products(self, term):
        data = []
        queryset = self.get_product_queryset()
        if term:
            queryset = queryset.filter(name__icontains=term)
        for product in queryset[:10]:
            item = product.toJSON()
            item['text'] = product.name
            data.append(item)
        return data

    def reset_totals(self, purchase):
        purchase.subtotal = Decimal('0.00')
        purchase.tax_total = Decimal('0.00')
        purchase.iva = Decimal('0.00')
        purchase.total = Decimal('0.00')
        purchase.balance = Decimal('0.00')
        purchase.save(update_fields=['subtotal', 'tax_total', 'iva', 'total', 'balance'])

    def get_required_int(self, value, message):
        try:
            if value in (None, ''):
                raise ValueError
            return int(value)
        except (TypeError, ValueError):
            raise Exception(message)

    def get_positive_int(self, value, message):
        number = self.get_required_int(value, message)
        if number <= 0:
            raise Exception(message)
        return number

    def get_decimal(self, value, message):
        try:
            return Decimal(str(value or 0))
        except Exception:
            raise Exception(message)

    @transaction.atomic
    def save_purchase_from_payload(self, payload):
        organization = self.get_current_organization()
        purchase = self.get_object() or Purchase(organization=organization)

        if purchase.pk and purchase.status != 'draft':
            raise Exception('Solo se pueden editar compras en borrador.')

        purchase.organization = organization
        supplier_id = self.get_required_int(payload.get('supplier'), 'Debe seleccionar un proveedor antes de registrar la compra.')
        if not Supplier.objects.filter(pk=supplier_id, organization=organization, is_active=True).exists():
            raise Exception('El proveedor seleccionado no pertenece a la tienda activa o esta inactivo.')

        products = payload.get('products') or []
        if not products:
            raise Exception('Debe ingresar al menos un producto en la factura.')

        purchase.supplier_id = supplier_id
        purchase.number = payload.get('number') or ''
        purchase.supplier_invoice = payload.get('supplier_invoice') or ''
        purchase.payment_term = payload.get('payment_term') or 'cash'
        purchase.date_joined = payload['date_joined']
        purchase.due_date = payload.get('due_date') or None
        purchase.amount_paid = self.get_decimal(payload.get('amount_paid', 0), 'El monto pagado no es valido.')
        purchase.observation = payload.get('observation') or ''
        purchase.full_clean()
        purchase.save()

        if purchase.pk and purchase.details.exists():
            purchase.details.all().delete()
            self.reset_totals(purchase)

        for item in products:
            product_id = self.get_required_int(item.get('id'), 'Hay un producto sin identificador valido en el detalle.')
            product = self.get_product_queryset().filter(pk=product_id).first()
            if product is None:
                raise Exception('El producto seleccionado no pertenece a la tienda activa o esta inactivo.')

            DetPurchase.objects.create(
                purchase=purchase,
                prod=product,
                cant=self.get_positive_int(item.get('cant'), 'La cantidad de cada producto debe ser mayor que cero.'),
                cost=self.get_decimal(item.get('cost', 0), 'El costo de cada producto debe ser numerico.'),
            )

        purchase.recalculate_totals()
        return purchase

    def get_details_product(self):
        obj = self.get_object()
        if obj is None:
            return []
        data = []
        for detail in obj.details.select_related('prod__cat', 'tax_rate'):
            item = detail.prod.toJSON()
            item['cost'] = format(detail.cost, '.2f')
            item['cant'] = detail.cant
            item['tax_rate'] = format(effective_tax_rate_percent(detail.tax_rate), '.2f')
            item['tax_amount'] = format(detail.tax_amount, '.2f')
            item['subtotal_before_tax'] = format(detail.subtotal_before_tax, '.2f')
            item['subtotal'] = format(detail.subtotal, '.2f')
            data.append(item)
        return data

    def get_context_data(self, **kwargs):
        obj = self.get_object()
        form = self.get_form()
        context = {
            'form': form,
            'title': self.title,
            'entity': 'Compras',
            'list_url': self.success_url,
            'action': self.action,
            'det': json.dumps(self.get_details_product()),
            'current_organization': self.get_current_organization(),
            'available_organizations': self.request.user.get_accessible_organizations(),
            'object': obj,
        }
        return context

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST.get('action')
            if action == 'search_products':
                data = self.search_products(request.POST.get('term', ''))
            elif action in ('add', 'edit'):
                payload = json.loads(request.POST['purchase'])
                self.save_purchase_from_payload(payload)
                data = {'success': True}
            else:
                data['error'] = 'No ha ingresado a ninguna opcion'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)


class PurchaseCreateView(PurchaseBaseEditorView):
    permission_required = 'erp.add_purchase'
    url_redirect = reverse_lazy('erp:purchase_list')
    title = 'Creacion de una Compra'
    action = 'add'


class PurchaseUpdateView(PurchaseBaseEditorView):
    permission_required = 'erp.change_purchase'
    url_redirect = reverse_lazy('erp:purchase_list')
    title = 'Edicion de una Compra'
    action = 'edit'


class PurchaseDeleteView(ERPAjaxDeleteView):
    model = Purchase
    template_name = 'delete.html'
    success_url = reverse_lazy('erp:purchase_list')
    permission_required = 'erp.delete_purchase'
    url_redirect = success_url
    title = 'Eliminacion de una Compra'
    entity = 'Compras'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            purchase = self.get_object()
            if purchase.status != 'draft':
                return JsonResponse({'error': 'Solo se pueden eliminar compras en borrador'})
            purchase.delete()
            data['success'] = True
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)


class PurchaseActionView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, View):
    template_name = 'purchase/action.html'
    action_method = ''
    action_label = ''
    title = ''
    permission_required = 'erp.change_purchase'
    url_redirect = reverse_lazy('erp:purchase_list')

    def get_object(self):
        return get_object_or_404(
            Purchase.objects.filter(organization=self.get_current_organization()).select_related('supplier'),
            pk=self.kwargs['pk'],
        )

    def get(self, request, *args, **kwargs):
        context = {
            'object': self.get_object(),
            'title': self.title,
            'entity': 'Compras',
            'list_url': reverse_lazy('erp:purchase_list'),
            'action_label': self.action_label,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        purchase = self.get_object()
        try:
            if self.action_method == 'confirm':
                purchase.confirm(user=request.user)
            elif self.action_method == 'cancel':
                purchase.cancel(reason=request.POST.get('reason', ''), user=request.user)
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)})


class PurchaseConfirmView(PurchaseActionView):
    action_method = 'confirm'
    action_label = 'Confirmar'
    title = 'Confirmacion de Compra'


class PurchaseCancelView(PurchaseActionView):
    action_method = 'cancel'
    action_label = 'Anular'
    title = 'Anulacion de Compra'
