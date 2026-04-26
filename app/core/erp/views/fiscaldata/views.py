from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View

from app.core.erp.forms import FiscalDataForm
from app.core.erp.mixins import CurrentOrganizationMixin
from app.core.erp.models import FiscalData
from app.core.erp.views.base import ERPAjaxCreateView, ERPAjaxUpdateView


class FiscalDataManageView(LoginRequiredMixin, CurrentOrganizationMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not (
            request.user.has_perm('erp.view_fiscaldata')
            or request.user.has_perm('erp.add_fiscaldata')
            or request.user.has_perm('erp.change_fiscaldata')
        ):
            messages.error(request, 'No tiene permiso para ingresar a este modulo')
            return redirect('erp:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        fiscal_data = FiscalData.objects.filter(organization=self.get_current_organization()).first()
        if fiscal_data:
            return redirect('erp:fiscaldata_update', pk=fiscal_data.pk)
        return redirect('erp:fiscaldata_create')


class FiscalDataCreateView(ERPAjaxCreateView):
    model = FiscalData
    form_class = FiscalDataForm
    template_name = 'form.html'
    success_url = reverse_lazy('erp:fiscaldata_manage')
    permission_required = 'erp.add_fiscaldata'
    url_redirect = success_url
    title = 'Configuracion de Datos Fiscales'
    entity = 'Datos fiscales'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        if not request.user.has_perm(self.permission_required):
            return super().dispatch(request, *args, **kwargs)

        fiscal_data = FiscalData.objects.filter(organization=self.get_current_organization()).first()
        if fiscal_data:
            return redirect('erp:fiscaldata_update', pk=fiscal_data.pk)
        return super().dispatch(request, *args, **kwargs)


class FiscalDataUpdateView(ERPAjaxUpdateView):
    model = FiscalData
    form_class = FiscalDataForm
    template_name = 'form.html'
    success_url = reverse_lazy('erp:fiscaldata_manage')
    permission_required = 'erp.change_fiscaldata'
    url_redirect = success_url
    title = 'Actualizacion de Datos Fiscales'
    entity = 'Datos fiscales'
