import json
import os
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction, models
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import get_template
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DeleteView, ListView
from xhtml2pdf import pisa

from app.core.erp.forms import ClientForm, SaleForm
from app.core.erp.mixins import CurrentOrganizationMixin, ValidatePermissionRequiredMixin
from app.core.erp.models import Client, DetSale, Product, Sale, effective_tax_rate_percent


class SaleListView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, ListView):
    model = Sale
    template_name = 'sale/list.html'
    permission_required = 'erp.view_sale'

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related('cli', 'cash_session', 'organization')
            .order_by('-date_joined', '-id')
        )

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST.get('action')
            if action == 'searchdata':
                # Compatibilidad:
                # - Si la petición incluye 'start' devolvemos el formato para DataTables
                # - Si no, devolvemos la lista simple de ventas (usada por los tests y llamadas AJAX simples)
                qs = self.get_queryset()
                if 'start' in request.POST:
                    try:
                        start = int(request.POST.get('start', 0))
                        length = int(request.POST.get('length', 100))
                    except Exception:
                        start = 0
                        length = 100
                    total = qs.count()
                    sales_qs = qs[start : start + length]
                    data = {
                        'recordsTotal': total,
                        'recordsFiltered': total,
                        'data': [sale.toJSON() for sale in sales_qs],
                    }
                else:
                    # Petición simple: retornar lista de objetos JSON
                    data = [sale.toJSON() for sale in qs]
            elif action == 'search_details_prod':
                sale_id = request.POST.get('id')
                data = [
                    detail.toJSON()
                    for detail in DetSale.objects.filter(
                        sale_id=sale_id,
                        sale__organization=self.get_current_organization(),
                    ).select_related('prod', 'sale')
                ]
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Ventas'
        context['create_url'] = reverse_lazy('erp:sale_create')
        context['list_url'] = reverse_lazy('erp:sale_list')
        context['entity'] = 'Ventas'
        context['can_create'] = self.request.user.has_perm('erp.add_sale')
        context['can_change'] = self.request.user.has_perm('erp.change_sale')
        context['can_delete'] = self.request.user.has_perm('erp.delete_sale')
        return context


class SaleBaseEditorView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, View):
    form_class = SaleForm
    template_name = 'sale/create.html'
    success_url = reverse_lazy('erp:sale_list')

    def get_object(self):
        if 'pk' not in self.kwargs:
            return None
        return get_object_or_404(
            Sale.objects.filter(organization=self.get_current_organization()).select_related('cli', 'cash_session'),
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

    def get_product_search_query(self, term):
        return (
            models.Q(name__icontains=term)
            | models.Q(barcode__icontains=term)
            | models.Q(internal_code__icontains=term)
            | models.Q(description__icontains=term)
            | models.Q(category__name__icontains=term)
            | models.Q(cat__name__icontains=term)
        )

    def search_products(self, term):
        data = []
        queryset = self.get_product_queryset()
        term = (term or '').strip()
        if term:
            # Buscar por nombre, código de barras o código interno para mayor flexibilidad
            for token in term.split():
                queryset = queryset.filter(self.get_product_search_query(token))
        for product in queryset.order_by('name')[:10]:
            item = product.toJSON()
            item['text'] = product.name
            data.append(item)
        return data

    def reset_totals(self, sale):
        sale.subtotal = Decimal('0.00')
        sale.tax_total = Decimal('0.00')
        sale.iva = Decimal('0.00')
        sale.total = Decimal('0.00')
        sale.balance = Decimal('0.00')
        sale.profit = Decimal('0.00')
        sale.save(update_fields=['subtotal', 'tax_total', 'iva', 'total', 'balance', 'profit'])

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
    def save_sale_from_payload(self, payload):
        organization = self.get_current_organization()
        sale = self.get_object() or Sale(organization=organization)

        if sale.pk and sale.status != 'draft':
            raise Exception('Solo se pueden editar ventas en borrador.')

        sale.organization = organization
        client_id = self.get_required_int(payload.get('cli'), 'Debe seleccionar un cliente antes de registrar la venta.')
        if not Client.objects.filter(pk=client_id, organization=organization, is_active=True).exists():
            raise Exception('El cliente seleccionado no pertenece a la tienda activa o esta inactivo.')

        products = payload.get('products') or []
        if not products:
            raise Exception('Debe ingresar al menos un producto en la venta.')

        sale.cli_id = client_id
        sale.cash_session_id = payload.get('cash_session') or None
        sale.document_type = payload.get('document_type') or 'invoice'
        sale.payment_term = payload.get('payment_term') or 'cash'
        sale.date_joined = payload['date_joined']
        sale.due_date = payload.get('due_date') or None
        sale.discount = self.get_decimal(payload.get('discount', 0), 'El descuento no es valido.')
        sale.amount_paid = self.get_decimal(payload.get('amount_paid', 0), 'El monto pagado no es valido.')
        # Prefer new 'tax_total' payload key, fallback to legacy 'iva'
        iva_amount = self.get_decimal(payload.get('tax_total', payload.get('iva', 0)), 'El impuesto no es valido.')
        if hasattr(sale, 'tax_total'):
            try:
                sale.tax_total = iva_amount
            except Exception:
                sale.tax_total = iva_amount
        sale.iva = iva_amount

        sale.observation = payload.get('observation') or ''
        sale.full_clean()
        sale.save()

        if sale.pk and sale.details.exists():
            sale.details.all().delete()
            self.reset_totals(sale)

        # Optimizar: obtener todos los productos en una sola consulta
        product_ids = []
        for item in products:
            product_ids.append(self.get_required_int(item.get('id'), 'Hay un producto sin identificador valido en el detalle.'))
        product_map = {p.id: p for p in self.get_product_queryset().filter(pk__in=product_ids)}

        for item in products:
            product_id = int(item.get('id'))
            product = product_map.get(product_id)
            if product is None:
                raise Exception('El producto seleccionado no pertenece a la tienda activa o esta inactivo.')

            DetSale.objects.create(
                sale=sale,
                prod=product,
                cant=self.get_positive_int(item.get('cant'), 'La cantidad de cada producto debe ser mayor que cero.'),
                price=self.get_decimal(item.get('price', 0), 'El precio de cada producto debe ser numerico.'),
                cost=self.get_decimal(item.get('cost', 0), 'El costo de cada producto debe ser numerico.'),
                discount=self.get_decimal(item.get('discount', 0), 'El descuento de cada producto debe ser numerico.'),
            )

        sale.recalculate_totals()
        return sale

    @transaction.atomic
    def save_legacy_sale_from_payload(self, payload):
        organization = self.get_current_organization()
        sale = self.get_object() or Sale(organization=organization)

        if sale.pk and sale.status != 'draft':
            raise Exception('Solo se pueden editar ventas en borrador.')

        sale.organization = organization
        client_id = self.get_required_int(payload.get('cli'), 'Debe seleccionar un cliente antes de registrar la venta.')
        if not Client.objects.filter(pk=client_id, organization=organization, is_active=True).exists():
            raise Exception('El cliente seleccionado no pertenece a la tienda activa o esta inactivo.')

        products = payload.get('products') or []
        if not products:
            raise Exception('Debe ingresar al menos un producto en la venta.')

        sale.cli_id = client_id
        sale.date_joined = payload['date_joined']
        sale.observation = payload.get('observation') or ''
        sale.amount_paid = self.get_decimal(payload.get('amount_paid', 0), 'El monto pagado no es valido.')
        sale.save()

        sale.details.all().delete()
        self.reset_totals(sale)

        # Optimizar: obtener todos los productos en una sola consulta
        product_ids = []
        for item in products:
            product_ids.append(self.get_required_int(item.get('id'), 'Hay un producto sin identificador valido en el detalle.'))
        product_map = {p.id: p for p in self.get_product_queryset().filter(pk__in=product_ids)}

        for item in products:
            product_id = int(item.get('id'))
            quantity = self.get_positive_int(item.get('cant'), 'La cantidad de cada producto debe ser mayor que cero.')
            product = product_map.get(product_id)
            if product is None:
                raise Exception('El producto seleccionado no pertenece a la tienda activa o esta inactivo.')

            DetSale.objects.create(
                sale=sale,
                prod=product,
                cant=quantity,
                price=self.get_decimal(item.get('price', item.get('pvp', 0)), 'El precio de cada producto debe ser numerico.'),
                cost=self.get_decimal(item.get('cost', 0), 'El costo de cada producto debe ser numerico.'),
            )

        # Accept 'tax_total' or legacy 'iva' and keep compatibility
        iva_amount = self.get_decimal(payload.get('tax_total', payload.get('iva', 0)), 'El impuesto no es valido.')
        if hasattr(sale, 'tax_total'):
            try:
                sale.tax_total = iva_amount
            except Exception:
                sale.tax_total = iva_amount
        sale.iva = iva_amount
        sale.calculate_totals(iva=iva_amount)
        return sale

    def get_details_product(self):
        obj = self.get_object()
        if obj is None:
            return []
        data = []
        for detail in obj.details.select_related('prod__cat', 'tax_rate'):
            item = detail.prod.toJSON()
            item['cant'] = detail.cant
            item['price'] = format(detail.price, '.2f')
            item['cost'] = format(detail.cost, '.2f')
            item['discount'] = format(detail.discount, '.2f')
            item['tax_rate'] = format(effective_tax_rate_percent(detail.tax_rate), '.2f')
            item['subtotal_before_tax'] = format(detail.subtotal_before_tax, '.2f')
            item['tax_amount'] = format(detail.tax_amount, '.2f')
            item['subtotal'] = format(detail.subtotal, '.2f')
            data.append(item)
        return data

    def get_context_data(self):
        obj = self.get_object()
        return {
            'form': self.get_form(),
            'title': self.title,
            'entity': 'Ventas',
            'list_url': self.success_url,
            'action': self.action,
            'det': json.dumps(self.get_details_product()),
            'current_organization': self.get_current_organization(),
            'available_organizations': self.request.user.get_accessible_organizations(),
            'object': obj,
        }

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST.get('action')
            if action == 'search_products':
                data = self.search_products(request.POST.get('term') or request.POST.get('q') or '')
            elif action == 'create_client':
                form = ClientForm(request.POST, request=request)
                if form.is_valid():
                    client = form.save_model()
                    data = {
                        'id': client.id,
                        'text': client.get_full_name(),
                        'full_name': client.get_full_name(),
                        'dni': client.dni or '',
                        'rtn': client.rtn or '',
                    }
                else:
                    data['error'] = form.errors
            elif action in ('add', 'edit'):
                payload_key = 'sale' if 'sale' in request.POST else 'vents'
                payload = json.loads(request.POST[payload_key])
                print_after_save = request.POST.get('print_after_save') == '1'
                if payload_key == 'vents':
                    sale = self.save_legacy_sale_from_payload(payload)
                else:
                    sale = self.save_sale_from_payload(payload)
                data = {'success': True, 'id': sale.id}
                if print_after_save:
                    try:
                        if sale.status == 'draft':
                            sale.confirm(user=request.user)
                        data['print_url'] = reverse('erp:sale_ticket_print', kwargs={'pk': sale.id})
                    except Exception as confirm_error:
                        data['warning'] = 'La venta se guardo en borrador, pero no se pudo imprimir/confirmar: {}'.format(confirm_error)
            else:
                data['error'] = 'No ha ingresado a ninguna opcion'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)


class SaleCreateView(SaleBaseEditorView):
    permission_required = 'erp.add_sale'
    url_redirect = reverse_lazy('erp:sale_list')
    title = 'Creacion de una Venta'
    action = 'add'


class SaleUpdateView(SaleBaseEditorView):
    permission_required = 'erp.change_sale'
    url_redirect = reverse_lazy('erp:sale_list')
    title = 'Edicion de una Venta'
    action = 'edit'


class SaleDeleteView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, DeleteView):
    model = Sale
    template_name = 'sale/delete.html'
    success_url = reverse_lazy('erp:sale_list')
    permission_required = 'erp.delete_sale'
    url_redirect = success_url

    def get_queryset(self):
        return Sale.objects.filter(organization=self.get_current_organization())

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            sale = self.get_object()
            if sale.status != 'draft':
                return JsonResponse({'error': 'Solo se pueden eliminar ventas en borrador'})
            sale.delete()
            data['success'] = True
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminacion de una Venta'
        context['entity'] = 'Ventas'
        context['list_url'] = self.success_url
        return context


class SaleActionView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, View):
    template_name = 'sale/action.html'
    action_method = ''
    action_label = ''
    title = ''
    permission_required = 'erp.change_sale'
    url_redirect = reverse_lazy('erp:sale_list')

    def get_object(self):
        return get_object_or_404(
            Sale.objects.filter(organization=self.get_current_organization()).select_related('cli'),
            pk=self.kwargs['pk'],
        )

    def get(self, request, *args, **kwargs):
        context = {
            'object': self.get_object(),
            'title': self.title,
            'entity': 'Ventas',
            'list_url': reverse_lazy('erp:sale_list'),
            'action_label': self.action_label,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        sale = self.get_object()
        try:
            if self.action_method == 'confirm':
                sale.confirm(user=request.user)
            elif self.action_method == 'cancel':
                sale.cancel(reason=request.POST.get('reason', ''), user=request.user)
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)})


class SaleConfirmView(SaleActionView):
    action_method = 'confirm'
    action_label = 'Confirmar'
    title = 'Confirmacion de Venta'


class SaleCancelView(SaleActionView):
    action_method = 'cancel'
    action_label = 'Anular'
    title = 'Anulacion de Venta'


class SaleInvoicePdfView(LoginRequiredMixin, CurrentOrganizationMixin, View):
    def link_callback(self, uri, rel):
        s_url = settings.STATIC_URL
        s_root = settings.STATIC_ROOT
        m_url = settings.MEDIA_URL
        m_root = settings.MEDIA_ROOT

        if uri.startswith(m_url):
            path = os.path.join(m_root, uri.replace(m_url, ''))
        elif uri.startswith(s_url):
            path = os.path.join(s_root, uri.replace(s_url, ''))
        else:
            return uri

        if not os.path.isfile(path):
            raise Exception('media URI must start with {} or {}'.format(s_url, m_url))
        return path

    def get_sale(self):
        return Sale.objects.select_related('organization', 'cli').get(
            pk=self.kwargs['pk'],
            organization=self.get_current_organization(),
        )

    def get(self, request, *args, **kwargs):
        try:
            sale = self.get_sale()
            organization = sale.organization or self.get_current_organization()
            fiscal_data = getattr(organization, 'fiscal_data', None)
            template = get_template('sale/invoice.html')
            context = {
                'sale': sale,
                'comp': {
                    'name': fiscal_data.business_name if fiscal_data else organization.name,
                    'ruc': fiscal_data.rtn if fiscal_data else (organization.rtn or 'N/D'),
                    'address': fiscal_data.address if fiscal_data else (organization.address or 'N/D'),
                },
                'icon': '{}{}'.format(settings.STATIC_URL, 'img/logo.png'),
            }
            html = template.render(context)
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="venta-{}.pdf"'.format(sale.id)
            pisa.CreatePDF(html, dest=response, link_callback=self.link_callback)
            return response
        except Exception:
            return HttpResponseRedirect(reverse_lazy('erp:sale_list'))


class SaleTicketPrintView(LoginRequiredMixin, CurrentOrganizationMixin, View):
    template_name = 'sale/ticket.html'

    def get_sale(self):
        return get_object_or_404(
            Sale.objects.filter(organization=self.get_current_organization())
            .select_related('organization', 'cli', 'cash_session')
            .prefetch_related('details__prod__category', 'details__prod__cat'),
            pk=self.kwargs['pk'],
        )

    def get(self, request, *args, **kwargs):
        sale = self.get_sale()
        organization = sale.organization or self.get_current_organization()
        fiscal_data = getattr(organization, 'fiscal_data', None)
        context = {
            'sale': sale,
            'organization': organization,
            'fiscal_data': fiscal_data,
            'company_name': (fiscal_data.trade_name or fiscal_data.business_name) if fiscal_data else organization.name,
            'company_rtn': fiscal_data.rtn if fiscal_data else (organization.rtn or 'N/D'),
            'company_address': fiscal_data.address if fiscal_data else (organization.address or 'N/D'),
            'company_phone': fiscal_data.phone if fiscal_data else (organization.phone or ''),
            'printed_at': timezone.localtime(timezone.now()),
        }
        return render(request, self.template_name, context)
