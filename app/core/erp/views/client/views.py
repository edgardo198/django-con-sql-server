from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from app.core.erp.forms import ClientForm
from app.core.erp.mixins import CurrentOrganizationMixin, ValidatePermissionRequiredMixin
from app.core.erp.models import Client


class ClientListView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, ListView):
    model = Client
    template_name = 'client/list.html'
    permission_required = 'erp.view_client'

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().order_by('names', 'surnames')

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            if request.POST['action'] == 'searchdata':
                data = [client.toJSON() for client in self.get_queryset()]
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Clientes'
        context['create_url'] = reverse_lazy('erp:client_create')
        context['list_url'] = reverse_lazy('erp:client_list')
        context['entity'] = 'Clientes'
        context['can_create'] = self.request.user.has_perm('erp.add_client')
        context['can_change'] = self.request.user.has_perm('erp.change_client')
        context['can_delete'] = self.request.user.has_perm('erp.delete_client')
        return context


class ClientCreateView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = 'client/create.html'
    success_url = reverse_lazy('erp:client_list')
    permission_required = 'erp.add_client'
    url_redirect = success_url

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            if request.POST['action'] == 'add':
                data = self.get_form().save()
            else:
                data['error'] = 'No ha ingresado a ninguna opcion'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Creacion de un Cliente'
        context['entity'] = 'Clientes'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        return context


class ClientUpdateView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = 'client/create.html'
    success_url = reverse_lazy('erp:client_list')
    permission_required = 'erp.change_client'
    url_redirect = success_url

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            if request.POST['action'] == 'edit':
                self.object = self.get_object()
                data = self.get_form().save()
            else:
                data['error'] = 'No ha ingresado a ninguna opcion'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edicion de un Cliente'
        context['entity'] = 'Clientes'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        return context


class ClientDeleteView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, DeleteView):
    model = Client
    template_name = 'client/delete.html'
    success_url = reverse_lazy('erp:client_list')
    permission_required = 'erp.delete_client'
    url_redirect = success_url

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminacion de un Cliente'
        context['entity'] = 'Clientes'
        context['list_url'] = self.success_url
        return context
