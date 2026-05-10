from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Min, Sum
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from app.core.erp.forms import SalePaymentForm
from app.core.erp.mixins import CurrentOrganizationMixin, ValidatePermissionRequiredMixin
from app.core.erp.models import Client, Sale, SalePayment


class AccountsReceivableListView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, ListView):
    model = Sale
    template_name = 'accountsreceivable/list.html'
    permission_required = 'erp.view_sale'
    url_redirect = reverse_lazy('erp:dashboard')

    def get_base_queryset(self):
        return (
            Sale.objects.filter(
                organization=self.get_current_organization(),
                status='confirmed',
                balance__gt=0,
            )
            .select_related('cli', 'cash_session')
            .prefetch_related('payments')
            .order_by('due_date', 'date_joined', 'id')
        )

    def get_queryset(self):
        queryset = self.get_base_queryset()
        client_id = self.request.GET.get('client')
        aging = self.request.GET.get('aging')
        today = timezone.localdate()

        if client_id:
            queryset = queryset.filter(cli_id=client_id)
        if aging == 'overdue':
            queryset = queryset.filter(due_date__lt=today)
        elif aging == 'due_today':
            queryset = queryset.filter(due_date=today)
        elif aging == 'open':
            queryset = queryset.filter(due_date__gte=today)
        elif aging == 'no_due_date':
            queryset = queryset.filter(due_date__isnull=True)
        return queryset

    def get_customer_summary(self):
        return (
            self.get_base_queryset()
            .values('cli_id', 'cli__names', 'cli__surnames', 'cli__phone', 'cli__credit_limit')
            .annotate(
                invoices=Count('id'),
                oldest_due_date=Min('due_date'),
                total_balance=Coalesce(Sum('balance'), Decimal('0.00')),
                total_amount=Coalesce(Sum('total'), Decimal('0.00')),
                total_paid=Coalesce(Sum('amount_paid'), Decimal('0.00')),
            )
            .order_by('-total_balance', 'cli__names')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = context['object_list']
        today = timezone.localdate()
        totals = queryset.aggregate(
            total_balance=Coalesce(Sum('balance'), Decimal('0.00')),
            total_amount=Coalesce(Sum('total'), Decimal('0.00')),
            total_paid=Coalesce(Sum('amount_paid'), Decimal('0.00')),
            invoices=Count('id'),
        )
        context.update(
            {
                'title': 'Cuentas por cobrar',
                'entity': 'Cuentas por cobrar',
                'list_url': reverse_lazy('erp:accounts_receivable_list'),
                'clients': Client.objects.filter(
                    organization=self.get_current_organization(),
                    sales__status='confirmed',
                    sales__balance__gt=0,
                ).distinct().order_by('names', 'surnames'),
                'customer_summary': self.get_customer_summary(),
                'totals': totals,
                'today': today,
                'selected_client': self.request.GET.get('client', ''),
                'selected_aging': self.request.GET.get('aging', ''),
                'can_add_payment': self.request.user.has_perm('erp.add_salepayment'),
            }
        )
        return context


class AccountsReceivableDetailView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, View):
    template_name = 'accountsreceivable/detail.html'
    permission_required = 'erp.view_sale'
    url_redirect = reverse_lazy('erp:accounts_receivable_list')

    def get_sale(self):
        return get_object_or_404(
            Sale.objects.filter(
                organization=self.get_current_organization(),
                status='confirmed',
            ).select_related('cli', 'cash_session'),
            pk=self.kwargs['pk'],
        )

    def get(self, request, *args, **kwargs):
        sale = self.get_sale()
        payments = SalePayment.objects.filter(
            organization=self.get_current_organization(),
            sale=sale,
        ).select_related('cash_session').order_by('-paid_at', '-id')
        context = {
            'title': 'Detalle de cuenta por cobrar',
            'entity': 'Cuentas por cobrar',
            'sale': sale,
            'payments': payments,
            'list_url': reverse_lazy('erp:accounts_receivable_list'),
            'payment_url': reverse_lazy('erp:accounts_receivable_payment', kwargs={'pk': sale.pk}),
            'can_add_payment': request.user.has_perm('erp.add_salepayment') and sale.balance > 0,
            'current_organization': self.get_current_organization(),
            'available_organizations': request.user.get_accessible_organizations(),
        }
        return render(request, self.template_name, context)


class AccountsReceivablePaymentView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, View):
    template_name = 'accountsreceivable/payment.html'
    permission_required = 'erp.add_salepayment'
    url_redirect = reverse_lazy('erp:accounts_receivable_list')

    def get_sale(self):
        return get_object_or_404(
            Sale.objects.filter(
                organization=self.get_current_organization(),
                status='confirmed',
                balance__gt=0,
            ).select_related('cli'),
            pk=self.kwargs['pk'],
        )

    def get_form(self):
        return SalePaymentForm(
            self.request.POST or None,
            request=self.request,
            sale=self.get_sale(),
        )

    def get_context_data(self, form=None):
        sale = self.get_sale()
        return {
            'form': form or self.get_form(),
            'sale': sale,
            'title': 'Registrar abono',
            'entity': 'Cuentas por cobrar',
            'list_url': reverse_lazy('erp:accounts_receivable_detail', kwargs={'pk': sale.pk}),
            'action': 'add',
            'current_organization': self.get_current_organization(),
            'available_organizations': self.request.user.get_accessible_organizations(),
        }

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            try:
                form.save_model()
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'error': str(e)})
        return JsonResponse({'error': form.errors.as_json()})
