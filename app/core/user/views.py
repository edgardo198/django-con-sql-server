from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, DeleteView, ListView, UpdateView, View

from app.core.erp.mixins import ValidatePermissionRequiredMixin
from app.core.user.forms import OrganizationForm, UserForm
from app.core.user.models import Organization, User


class OrganizationAccessMixin(object):
    def get_organization_queryset(self):
        queryset = Organization.objects.all().order_by('name')
        if self.request.user.is_superuser:
            return queryset
        return queryset.filter(pk__in=self.request.user.organizations.values_list('pk', flat=True))


class UserAccessMixin(object):
    def get_user_queryset(self):
        if not self.request.user.is_authenticated:
            return User.objects.none()
        return self.request.user.get_manageable_users_queryset()


class OrganizationListView(LoginRequiredMixin, ValidatePermissionRequiredMixin, OrganizationAccessMixin, ListView):
    model = Organization
    template_name = 'organization/list.html'
    permission_required = 'user.view_organization'

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.get_organization_queryset()

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            if request.POST['action'] == 'searchdata':
                data = [organization.toJSON() for organization in self.get_queryset()]
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Tiendas'
        context['create_url'] = reverse_lazy('user:organization_create')
        context['list_url'] = reverse_lazy('user:organization_list')
        context['entity'] = 'Tiendas'
        context['can_create'] = self.request.user.has_perm('user.add_organization')
        context['can_change'] = self.request.user.has_perm('user.change_organization')
        context['can_delete'] = self.request.user.has_perm('user.delete_organization')
        current_organization = self.request.user.get_current_organization()
        context['current_organization_id'] = current_organization.id if current_organization else None
        return context


class OrganizationCreateView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CreateView):
    model = Organization
    form_class = OrganizationForm
    template_name = 'form.html'
    success_url = reverse_lazy('user:organization_list')
    permission_required = 'user.add_organization'
    url_redirect = success_url

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            if request.POST['action'] == 'add':
                form = self.get_form()
                data = form.save()
                if not data and request.user.is_authenticated:
                    organization = form.instance
                    request.user.organizations.add(organization)
                    request.user.set_current_organization(organization)
            else:
                data['error'] = 'No ha ingresado a ninguna opcion'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Creacion de una Tienda'
        context['entity'] = 'Tiendas'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        return context


class OrganizationUpdateView(LoginRequiredMixin, ValidatePermissionRequiredMixin, OrganizationAccessMixin, UpdateView):
    model = Organization
    form_class = OrganizationForm
    template_name = 'form.html'
    success_url = reverse_lazy('user:organization_list')
    permission_required = 'user.change_organization'
    url_redirect = success_url

    def get_queryset(self):
        return self.get_organization_queryset()

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            if request.POST['action'] == 'edit':
                self.object = self.get_object()
                form = self.get_form()
                data = form.save()
            else:
                data['error'] = 'No ha ingresado a ninguna opcion'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edicion de una Tienda'
        context['entity'] = 'Tiendas'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        return context


class OrganizationDeleteView(LoginRequiredMixin, ValidatePermissionRequiredMixin, OrganizationAccessMixin, DeleteView):
    model = Organization
    template_name = 'delete.html'
    success_url = reverse_lazy('user:organization_list')
    permission_required = 'user.delete_organization'
    url_redirect = success_url

    def get_queryset(self):
        return self.get_organization_queryset()

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            organization = self.get_object()
            if request.user.current_organization_id == organization.id:
                data['error'] = 'No puede eliminar la tienda que tiene activa. Cambie de tienda antes de continuar.'
            elif (
                organization.users.exists()
                or organization.categories.exists()
                or organization.products.exists()
                or organization.clients.exists()
                or organization.sales.exists()
            ):
                organization.is_active = False
                organization.save(update_fields=['is_active'])
            else:
                organization.delete()
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminacion de una Tienda'
        context['entity'] = 'Tiendas'
        context['list_url'] = self.success_url
        return context


class SwitchOrganizationView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        organization = Organization.objects.filter(pk=kwargs['pk'], is_active=True).first()
        if organization and request.user.set_current_organization(organization):
            return redirect(request.META.get('HTTP_REFERER') or reverse_lazy('erp:dashboard'))
        return redirect(reverse_lazy('erp:dashboard'))


class MenuLayoutToggleView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        current_layout = request.session.get('menu_layout', 'vtc')
        selected_layout = request.GET.get('layout')

        if selected_layout not in ['hzt', 'vtc']:
            selected_layout = 'vtc' if current_layout == 'hzt' else 'hzt'

        request.session['menu_layout'] = selected_layout
        request.session['menu_layout_template'] = f'{selected_layout}/body.html'
        return redirect(request.META.get('HTTP_REFERER') or reverse_lazy('erp:dashboard'))


class UserListView(LoginRequiredMixin, ValidatePermissionRequiredMixin, UserAccessMixin, ListView):
    model = User
    template_name = 'user/list.html'
    permission_required = 'user.view_user'

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.get_user_queryset()

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            if request.POST['action'] == 'searchdata':
                data = [user.toJSON() for user in self.get_queryset()]
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Usuarios'
        context['create_url'] = reverse_lazy('user:user_create')
        context['list_url'] = reverse_lazy('user:user_list')
        context['entity'] = 'Usuarios'
        context['can_create'] = self.request.user.has_perm('user.add_user')
        context['can_change'] = self.request.user.has_perm('user.change_user')
        context['can_delete'] = self.request.user.has_perm('user.delete_user')
        return context


class UserCreateView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CreateView):
    model = User
    form_class = UserForm
    template_name = 'user/create.html'
    success_url = reverse_lazy('user:user_list')
    permission_required = 'user.add_user'
    url_redirect = success_url

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            if request.POST['action'] == 'add':
                form = self.get_form()
                data = form.save()
            else:
                data['error'] = 'No ha ingresado a ninguna opcion'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Creacion de un Usuario'
        context['entity'] = 'Usuarios'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        return context


class UserUpdateView(LoginRequiredMixin, ValidatePermissionRequiredMixin, UserAccessMixin, UpdateView):
    model = User
    form_class = UserForm
    template_name = 'user/create.html'
    success_url = reverse_lazy('user:user_list')
    permission_required = 'user.change_user'
    url_redirect = success_url

    def get_queryset(self):
        return self.get_user_queryset()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            if request.POST['action'] == 'edit':
                user = self.get_object()
                form = self.form_class(
                    request.POST,
                    request.FILES,
                    instance=user,
                    request=request,
                )
                data = form.save()
            else:
                data['error'] = 'No ha ingresado a ninguna opcion'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edicion de un Usuario'
        context['entity'] = 'Usuarios'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        return context


class UserDeleteView(LoginRequiredMixin, ValidatePermissionRequiredMixin, UserAccessMixin, DeleteView):
    model = User
    template_name = 'user/delete.html'
    success_url = reverse_lazy('user:user_list')
    permission_required = 'user.delete_user'
    url_redirect = success_url

    def get_queryset(self):
        return self.get_user_queryset()

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            user = self.get_object()
            if user.pk == request.user.pk:
                data['error'] = 'No puede eliminar su propio usuario.'
            else:
                user.delete()
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminacion de un Usuario'
        context['entity'] = 'Usuarios'
        context['list_url'] = self.success_url
        return context
