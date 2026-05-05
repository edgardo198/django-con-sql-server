from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Max, Sum
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.generic import TemplateView

from app.core.erp.mixins import CurrentOrganizationMixin, ValidatePermissionRequiredMixin
from app.core.erp.models import Sale
from app.core.reports.forms import ReportForm


class ReportSaleView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CurrentOrganizationMixin, TemplateView):
    template_name = 'sale/report.html'
    permission_required = 'erp.view_sale'
    url_redirect = reverse_lazy('erp:dashboard')

    def get_sales_queryset(self):
        return Sale.objects.filter(organization=self.get_current_organization()).select_related('cli', 'organization')

    def get_report_base_date(self):
        today = timezone.localdate()
        queryset = self.get_sales_queryset()
        if queryset.filter(date_joined__year=today.year, date_joined__month=today.month).exists():
            return today
        return queryset.aggregate(last_sale=Max('date_joined')).get('last_sale') or today

    def get_tax_field_name(self):
        field_names = {field.name for field in Sale._meta.get_fields()}
        return 'tax_total' if 'tax_total' in field_names else 'iva'

    def get_period_range(self, period, start_date='', end_date=''):
        today = self.get_report_base_date()
        period = period or 'month'
        parsed_end = parse_date(end_date) if end_date else None
        base_date = parsed_end or today

        if period == 'day':
            return base_date.strftime('%Y-%m-%d'), base_date.strftime('%Y-%m-%d'), 'Hoy'

        if period == 'week':
            week_start = base_date - timedelta(days=base_date.weekday())
            return week_start.strftime('%Y-%m-%d'), base_date.strftime('%Y-%m-%d'), 'Semana'

        if period == 'custom':
            parsed_start = parse_date(start_date) if start_date else None
            start = parsed_start or today.replace(day=1)
            end = parsed_end or base_date
            if start > end:
                start, end = end, start
            return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'), 'Rango manual'

        month_start = base_date.replace(day=1)
        return month_start.strftime('%Y-%m-%d'), base_date.strftime('%Y-%m-%d'), 'Mes'

    def build_summary(self, queryset):
        subtotal = queryset.aggregate(r=Sum('subtotal')).get('r') or 0
        tax_total = queryset.aggregate(r=Sum(self.get_tax_field_name())).get('r') or 0
        total = queryset.aggregate(r=Sum('total')).get('r') or 0
        profit = queryset.aggregate(r=Sum('profit')).get('r') or 0
        sales_count = queryset.count()
        total_items = queryset.aggregate(r=Sum('details__cant')).get('r') or 0
        average_ticket = total / sales_count if sales_count else 0

        return {
            'subtotal': float(subtotal),
            'iva': float(tax_total),
            'tax_total': float(tax_total),
            'total': float(total),
            'profit': float(profit),
            'sales_count': sales_count,
            'total_items': int(total_items),
            'average_ticket': float(average_ticket),
        }

    def build_rows(self, queryset):
        data = []
        tax_field_name = self.get_tax_field_name()
        for sale in queryset.order_by('-date_joined', '-id'):
            items_count = sale.details.aggregate(r=Sum('cant')).get('r') or 0
            tax_total = getattr(sale, tax_field_name, 0) or 0
            data.append({
                'id': sale.id,
                'organization': sale.organization.name if sale.organization else 'Sin tienda',
                'client': sale.cli.get_full_name(),
                'date_joined': sale.date_joined.strftime('%Y-%m-%d'),
                'items_count': int(items_count or 0),
                'subtotal': float(sale.subtotal),
                'tax_total': float(tax_total),
                'iva': float(tax_total),
                'total': float(sale.total),
                'profit': float(sale.profit),
                'status': sale.get_status_display(),
            })
        return data

    def build_top_clients(self, queryset):
        clients = (
            queryset.values('cli__names', 'cli__surnames')
            .annotate(total=Sum('total'), sales_count=Count('id'))
            .order_by('-total')[:5]
        )
        return [
            {
                'names': item['cli__names'] or '',
                'surnames': item['cli__surnames'] or '',
                'total': float(item['total'] or 0),
                'sales_count': item['sales_count'],
            }
            for item in clients
        ]

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'search_report':
                period = request.POST.get('period', 'month')
                start_date, end_date, period_label = self.get_period_range(
                    period,
                    request.POST.get('start_date', ''),
                    request.POST.get('end_date', ''),
                )
                queryset = self.get_sales_queryset()
                if start_date:
                    queryset = queryset.filter(date_joined__gte=start_date)
                if end_date:
                    queryset = queryset.filter(date_joined__lte=end_date)

                data = {
                    'rows': self.build_rows(queryset),
                    'summary': self.build_summary(queryset),
                    'period': period,
                    'period_label': period_label,
                    'start_date': start_date,
                    'end_date': end_date,
                    'top_clients': self.build_top_clients(queryset),
                }
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Reporte de Venta'
        context['entity'] = 'Reporte'
        context['list_url'] = reverse_lazy('sale_report')
        context['form'] = ReportForm()
        context['current_organization'] = self.get_current_organization()
        base_date = self.get_report_base_date()
        context['report_default_start_date'] = base_date.replace(day=1).strftime('%Y-%m-%d')
        context['report_default_end_date'] = base_date.strftime('%Y-%m-%d')
        context['report_default_period'] = 'month'
        return context
