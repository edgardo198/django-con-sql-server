from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Q
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from app.core.erp.forms import ProductForm
from app.core.erp.mixins import CurrentOrganizationMixin, ValidatePermissionRequiredMixin
from app.core.erp.models import Product


class ProductListView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, ListView):
    model = Product
    template_name = 'product/list.html'
    permission_required = 'erp.view_product'

    def get_current_org(self):
        return self.get_current_organization()

    def product_has_field(self, field_name):
        return any(field.name == field_name for field in Product._meta.fields)

    def get_search_query(self, search):
        query = Q(name__icontains=search) | Q(barcode__icontains=search)
        if self.product_has_field('internal_code'):
            query |= Q(internal_code__icontains=search)
        return query

    def set_display_fields(self, products):
        for product in products:
            product.display_code = product.barcode or getattr(product, 'internal_code', None) or '-'
        return products

    def get_queryset(self):
        queryset = (
            Product.objects
            .filter(organization=self.get_current_org())
            .select_related('category', 'cat', 'tax_rate', 'organization')
            .order_by('name')
        )

        search = self.request.GET.get('search', '').strip()
        stock_status = self.request.GET.get('stock_status', '').strip()

        if search:
            queryset = queryset.filter(self.get_search_query(search))

        if stock_status == 'available':
            queryset = queryset.filter(stock__gt=0)
        elif stock_status == 'low':
            queryset = queryset.filter(stock__lte=F('min_stock'))

        return queryset

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST.get('action')

            if action == 'searchdata':
                data = [product.toJSON() for product in self.get_queryset()]

            elif action == 'search_by_term':
                term = request.POST.get('term', '').strip()
                queryset = self.get_queryset()

                if term:
                    queryset = queryset.filter(self.get_search_query(term))

                data = [product.toJSON() for product in queryset[:20]]

            elif action == 'validate_barcode':
                barcode = request.POST.get('barcode', '').strip()
                pk = request.POST.get('id')
                qs = Product.objects.filter(
                    organization=self.get_current_org(),
                    barcode=barcode
                )
                if pk and str(pk).isdigit():
                    qs = qs.exclude(pk=int(pk))

                data = {
                    'valid': not qs.exists(),
                    'message': 'Código disponible' if not qs.exists() else 'Ese código ya existe'
                }
            else:
                data['error'] = 'Acción no válida'

        except Exception as e:
            data['error'] = str(e)

        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_list'] = self.set_display_fields(list(context['object_list']))
        context['title'] = 'Listado de Productos'
        context['create_url'] = reverse_lazy('erp:product_create')
        context['list_url'] = reverse_lazy('erp:product_list')
        context['entity'] = 'Productos'
        context['can_create'] = self.request.user.has_perm('erp.add_product')
        context['can_change'] = self.request.user.has_perm('erp.change_product')
        context['can_delete'] = self.request.user.has_perm('erp.delete_product')
        context['search'] = self.request.GET.get('search', '')
        context['stock_status'] = self.request.GET.get('stock_status', '')
        return context


class ProductCreateView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'product/create.html'
    success_url = reverse_lazy('erp:product_list')
    permission_required = 'erp.add_product'
    url_redirect = success_url

    def form_valid(self, form):
        form.instance.organization = self.get_current_organization()
        return super().form_valid(form)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST.get('action')

            if action == 'add':
                form = self.get_form()

                if form.is_valid():
                    form.instance.organization = self.get_current_organization()

                    barcode = form.cleaned_data.get('barcode')
                    if barcode and Product.objects.filter(
                        organization=self.get_current_organization(),
                        barcode=barcode
                    ).exists():
                        return JsonResponse({'error': 'Ya existe un producto con ese código de barras'})

                    obj = form.save_model()
                    data = obj.toJSON() if hasattr(obj, 'toJSON') else {'success': True}
                else:
                    data['error'] = form.errors
            else:
                data['error'] = 'No ha ingresado a ninguna opción válida'

        except Exception as e:
            data['error'] = str(e)

        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Creación de un Producto'
        context['entity'] = 'Productos'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        return context


class ProductUpdateView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'product/create.html'
    success_url = reverse_lazy('erp:product_list')
    permission_required = 'erp.change_product'
    url_redirect = success_url

    def get_queryset(self):
        return Product.objects.filter(organization=self.get_current_organization())

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST.get('action')

            if action == 'edit':
                self.object = self.get_object()
                form = self.get_form()

                if form.is_valid():
                    barcode = form.cleaned_data.get('barcode')
                    if barcode and Product.objects.filter(
                        organization=self.get_current_organization(),
                        barcode=barcode
                    ).exclude(pk=self.get_object().pk).exists():
                        return JsonResponse({'error': 'Ya existe otro producto con ese código de barras'})

                    obj = form.save_model()
                    data = obj.toJSON() if hasattr(obj, 'toJSON') else {'success': True}
                else:
                    data['error'] = form.errors
            else:
                data['error'] = 'No ha ingresado a ninguna opción válida'

        except Exception as e:
            data['error'] = str(e)

        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edición de un Producto'
        context['entity'] = 'Productos'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        return context


class ProductDeleteView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, DeleteView):
    model = Product
    template_name = 'product/delete.html'
    success_url = reverse_lazy('erp:product_list')
    permission_required = 'erp.delete_product'
    url_redirect = success_url

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Product.objects.filter(organization=self.get_current_organization())

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            obj = self.get_object()

            if obj.sale_details.exists():
                return JsonResponse({'error': 'No se puede eliminar el producto porque ya tiene ventas registradas'})

            if obj.purchase_details.exists():
                return JsonResponse({'error': 'No se puede eliminar el producto porque ya tiene compras registradas'})

            obj.delete()
            data = {'success': True}
        except Exception as e:
            data['error'] = str(e)

        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminación de un Producto'
        context['entity'] = 'Productos'
        context['list_url'] = self.success_url
        return context
