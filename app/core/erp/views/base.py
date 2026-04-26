from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from app.core.erp.mixins import CurrentOrganizationMixin, ValidatePermissionRequiredMixin


class ERPTableListView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, ListView):
    template_name = 'shared/model_list.html'
    title = ''
    entity = ''
    create_url_name = None
    update_url_name = None
    delete_url_name = None
    can_create_permission = ''
    can_change_permission = ''
    can_delete_permission = ''
    show_actions = True

    def get_table_columns(self):
        return []

    def get_row_cells(self, obj):
        return []

    def get_row_actions(self, obj):
        actions = []

        if self.update_url_name and self.request.user.has_perm(self.can_change_permission):
            actions.append({
                'label': 'Editar',
                'icon': 'fas fa-edit',
                'url': reverse_lazy(self.update_url_name, kwargs={'pk': obj.pk}),
                'class': 'btn btn-primary btn-xs btn-flat',
            })

        if self.delete_url_name and self.request.user.has_perm(self.can_delete_permission):
            actions.append({
                'label': 'Eliminar',
                'icon': 'fas fa-trash-alt',
                'url': reverse_lazy(self.delete_url_name, kwargs={'pk': obj.pk}),
                'class': 'btn btn-danger btn-xs btn-flat',
            })

        return actions

    def get_table_rows(self):
        return [
            {
                'cells': self.get_row_cells(obj),
                'actions': self.get_row_actions(obj),
            }
            for obj in self.get_queryset()
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        context['entity'] = self.entity
        context['list_url'] = self.request.path
        context['create_url'] = reverse_lazy(self.create_url_name) if self.create_url_name else None
        context['can_create'] = bool(self.create_url_name) and self.request.user.has_perm(self.can_create_permission)
        context['show_actions'] = self.show_actions
        context['table_columns'] = self.get_table_columns()
        context['table_rows'] = self.get_table_rows()
        return context


class ERPBaseFormViewMixin:
    entity = ''
    title = ''

    def form_invalid_response(self, form):
        return JsonResponse({'error': form.errors})

    def form_valid_response(self, form):
        instance = form.save_model()
        if hasattr(instance, 'toJSON'):
            return JsonResponse(instance.toJSON(), safe=False)
        return JsonResponse({'success': True, 'id': instance.pk})

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid_response(form)
        return self.form_invalid_response(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        context['entity'] = self.entity
        context['list_url'] = self.success_url
        return context


class ERPAjaxCreateView(ERPBaseFormViewMixin, LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, CreateView):
    action = 'add'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = self.action
        return context


class ERPAjaxUpdateView(ERPBaseFormViewMixin, LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, UpdateView):
    action = 'edit'

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = self.action
        return context


class ERPAjaxDeleteView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, DeleteView):
    entity = ''
    title = ''

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.pop('request', None)
        return kwargs

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
            data['success'] = True
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.title
        context['entity'] = self.entity
        context['list_url'] = self.success_url
        return context
