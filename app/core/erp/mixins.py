import inspect
from datetime import datetime

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy


class IsSuperuserMixin(object):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        return redirect('index')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['date_now'] = datetime.now()
        return context


class ValidatePermissionRequiredMixin(object):
    permission_required = ''
    url_redirect = None

    def get_perms(self):
        if isinstance(self.permission_required, str):
            perms = (self.permission_required,)
        else:
            perms = self.permission_required
        return perms

    def get_url_redirect(self):
        if self.url_redirect is None:
            return reverse_lazy('index')
        return self.url_redirect

    def dispatch(self, request, *args, **kwargs):
        if request.user.has_perms(self.get_perms()):
            return super().dispatch(request, *args, **kwargs)
        messages.error(request, 'No tiene permiso para ingresar a este modulo')
        return HttpResponseRedirect(self.get_url_redirect())


class CurrentOrganizationMixin(object):
    @staticmethod
    def form_accepts_request(form_class):
        try:
            parameters = inspect.signature(form_class.__init__).parameters
        except (TypeError, ValueError):
            return False
        return 'request' in parameters or any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in parameters.values()
        )

    def get_current_organization(self):
        organization = self.request.user.get_current_organization()
        if organization is None:
            raise PermissionDenied('No existe una tienda activa para este usuario.')
        return organization

    def filter_queryset_by_organization(self, queryset):
        if hasattr(queryset.model, 'organization_id'):
            return queryset.filter(organization=self.get_current_organization())
        return queryset

    def get_queryset(self):
        queryset = super().get_queryset()
        return self.filter_queryset_by_organization(queryset)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        form_class = self.get_form_class() if hasattr(self, 'get_form_class') else None
        if form_class and self.form_accepts_request(form_class):
            kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_organization'] = self.get_current_organization()
        context['available_organizations'] = self.request.user.get_accessible_organizations()
        return context
