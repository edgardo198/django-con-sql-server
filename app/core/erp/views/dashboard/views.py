import calendar
import csv
import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, F, Sum
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from app.core.erp.mixins import CurrentOrganizationMixin
from app.core.erp.models import DetSale, InventoryMovement, Product, Sale


class DashboardView(LoginRequiredMixin, CurrentOrganizationMixin, TemplateView):
    template_name = 'dashboard.html'

    month_names = [
        'Enero',
        'Febrero',
        'Marzo',
        'Abril',
        'Mayo',
        'Junio',
        'Julio',
        'Agosto',
        'Septiembre',
        'Octubre',
        'Noviembre',
        'Diciembre',
    ]

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def _to_float(self, value):
        return float(value or 0)

    def _to_int(self, value):
        return int(value or 0)

    def get_selected_year(self, raw_year=None):
        current_year = timezone.localdate().year
        try:
            return int(raw_year or current_year)
        except (TypeError, ValueError):
            return current_year

    def get_selected_month(self, raw_month=None):
        current_month = timezone.localdate().month
        try:
            month = int(raw_month or current_month)
        except (TypeError, ValueError):
            return current_month
        return month if 1 <= month <= 12 else current_month

    def get_current_org(self):
        return self.get_current_organization()

    def get_sales_queryset(self):
        return (
            Sale.objects.filter(organization=self.get_current_org())
            .select_related('cli', 'organization')
            .order_by('-date_joined', '-id')
        )

    def get_products_queryset(self):
        return (
            Product.objects.filter(organization=self.get_current_org())
            .select_related('category', 'cat')
            .order_by('name')
        )

    def get_movements_queryset(self):
        return (
            InventoryMovement.objects.filter(organization=self.get_current_org())
            .select_related('product')
            .order_by('-date_joined', '-id')
        )

    def get_available_years(self):
        current_year = timezone.localdate().year
        years = {current_year, current_year - 1}
        years.update(date.year for date in self.get_sales_queryset().dates('date_joined', 'year'))
        return sorted(years, reverse=True)

    def get_monthly_totals(self, year):
        totals = {month: 0.0 for month in range(1, 13)}

        rows = (
            self.get_sales_queryset()
            .filter(date_joined__year=year)
            .values('date_joined__month')
            .annotate(total_amount=Sum('total'))
            .order_by('date_joined__month')
        )

        for row in rows:
            totals[row['date_joined__month']] = self._to_float(row['total_amount'])

        return [totals[month] for month in range(1, 13)]

    def get_daily_totals(self, year, month):
        days_in_month = calendar.monthrange(year, month)[1]
        totals = {day: 0.0 for day in range(1, days_in_month + 1)}

        rows = (
            self.get_sales_queryset()
            .filter(date_joined__year=year, date_joined__month=month)
            .values('date_joined__day')
            .annotate(total_amount=Sum('total'))
            .order_by('date_joined__day')
        )

        for row in rows:
            totals[row['date_joined__day']] = self._to_float(row['total_amount'])

        return {
            'categories': [str(day) for day in range(1, days_in_month + 1)],
            'series': [
                {
                    'name': 'Ventas diarias',
                    'data': [totals[day] for day in range(1, days_in_month + 1)],
                }
            ],
        }

    def get_top_product_summary(self, year, month):
        row = (
            DetSale.objects.filter(
                sale__organization=self.get_current_org(),
                sale__date_joined__year=year,
                sale__date_joined__month=month,
            )
            .values('prod__name')
            .annotate(
                quantity=Sum('cant'),
                value=Sum('subtotal'),
            )
            .order_by('-value', '-quantity', 'prod__name')
            .first()
        )

        if not row:
            return {
                'name': 'Sin ventas',
                'quantity': 0,
                'value': 0.0,
            }

        return {
            'name': row['prod__name'],
            'quantity': self._to_int(row['quantity']),
            'value': self._to_float(row['value']),
        }

    def get_top_products_chart(self, year, month):
        rows = (
            DetSale.objects.filter(
                sale__organization=self.get_current_org(),
                sale__date_joined__year=year,
                sale__date_joined__month=month,
            )
            .values('prod__name')
            .annotate(
                quantity=Sum('cant'),
                value=Sum('subtotal'),
            )
            .order_by('-value', '-quantity', 'prod__name')[:5]
        )
        return [
            {
                'name': row['prod__name'],
                'y': self._to_float(row['value']),
                'quantity': self._to_int(row['quantity']),
            }
            for row in rows
        ]

    def get_top_client_summary(self, year, month):
        row = (
            self.get_sales_queryset()
            .filter(date_joined__year=year, date_joined__month=month)
            .values('cli__names', 'cli__surnames')
            .annotate(
                value=Sum('total'),
                sales_count=Count('id'),
            )
            .order_by('-value', '-sales_count', 'cli__names', 'cli__surnames')
            .first()
        )

        if not row:
            return {
                'name': 'Sin ventas',
                'value': 0.0,
                'sales_count': 0,
            }

        full_name = '{} {}'.format(
            row['cli__names'] or '',
            row['cli__surnames'] or '',
        ).strip()

        return {
            'name': full_name or 'Cliente sin nombre',
            'value': self._to_float(row['value']),
            'sales_count': self._to_int(row['sales_count']),
        }

    def get_top_clients_chart(self, year, month):
        rows = (
            self.get_sales_queryset()
            .filter(date_joined__year=year, date_joined__month=month)
            .values('cli__names', 'cli__surnames')
            .annotate(
                total_amount=Sum('total'),
                sales_count=Count('id'),
            )
            .order_by('-total_amount', '-sales_count', 'cli__names', 'cli__surnames')[:5]
        )
        categories = []
        data = []

        for row in rows:
            full_name = '{} {}'.format(
                row['cli__names'] or '',
                row['cli__surnames'] or '',
            ).strip()

            categories.append(full_name or 'Cliente sin nombre')
            data.append({
                'y': self._to_float(row['total_amount']),
                'sales_count': self._to_int(row['sales_count']),
            })

        return {
            'categories': categories,
            'series': [
                {
                    'name': 'Clientes',
                    'data': data,
                }
            ],
        }

    def get_inventory_snapshot(self):
        low_stock_products = [
            {
                'name': product.name,
                'stock': self._to_int(product.stock),
                'min_stock': self._to_int(product.min_stock),
                'barcode': product.barcode or '',
                'category': (product.category or product.cat).name if (product.category or product.cat) else '',
            }
            for product in self.get_products_queryset()
            .filter(stock__lte=F('min_stock'))
            .order_by('stock', 'name')[:5]
        ]
        recent_movements = [
            {
                'product': movement.product.name,
                'type': movement.get_movement_type_display(),
                'quantity': self._to_int(movement.quantity),
                'reference': movement.reference or '',
                'date_joined': timezone.localtime(movement.date_joined).strftime('%Y-%m-%d %H:%M'),
            }
            for movement in self.get_movements_queryset()[:5]
        ]
        return {
            'low_stock_products': low_stock_products,
            'recent_movements': recent_movements,
        }

    def get_profit_month(self, year, month):
        value = (
            self.get_sales_queryset()
            .filter(date_joined__year=year, date_joined__month=month)
            .aggregate(total_profit=Sum('profit'))
            .get('total_profit')
        )
        return value or Decimal('0.00')

    def get_dashboard_overview(self, year, month):
        current_organization = self.get_current_org()
        sales = self.get_sales_queryset()
        year_sales = sales.filter(date_joined__year=year)
        month_sales = year_sales.filter(date_joined__month=month)
        products = self.get_products_queryset()
        movements = self.get_movements_queryset()

        monthly_totals = self.get_monthly_totals(year)
        previous_year_totals = self.get_monthly_totals(year - 1)

        revenue_year = year_sales.aggregate(total_amount=Sum('total')).get('total_amount') or Decimal('0.00')
        revenue_month = month_sales.aggregate(total_amount=Sum('total')).get('total_amount') or Decimal('0.00')
        profit_month = self.get_profit_month(year, month)

        sales_count_year = year_sales.count()
        sales_count_month = month_sales.count()

        inventory_movements_month = movements.filter(
            date_joined__year=year,
            date_joined__month=month,
        ).count()

        total_stock_units = products.aggregate(total_amount=Sum('stock')).get('total_amount') or 0
        low_stock_count = products.filter(stock__lte=F('min_stock')).count()
        total_products = products.count()

        average_ticket = (revenue_month / sales_count_month) if sales_count_month else Decimal('0.00')
        average_ticket_year = (revenue_year / sales_count_year) if sales_count_year else Decimal('0.00')
        best_month_value = max(monthly_totals) if monthly_totals else 0
        best_month_index = monthly_totals.index(best_month_value) if best_month_value else 0

        top_product = self.get_top_product_summary(year, month)
        top_client = self.get_top_client_summary(year, month)

        return {
            'filters': {
                'available_years': self.get_available_years(),
                'selected_year': year,
                'selected_month': month,
                'selected_month_name': self.month_names[month - 1],
                'selected_organization': current_organization.name if current_organization else '',
            },
            'summary': {
                'revenue_year': self._to_float(revenue_year),
                'revenue_month': self._to_float(revenue_month),
                'profit_month': self._to_float(profit_month),
                'average_ticket': self._to_float(average_ticket),
                'average_ticket_year': self._to_float(average_ticket_year),
                'sales_count_year': sales_count_year,
                'sales_count_month': sales_count_month,
                'sales_last_7_days_count': self.get_sales_last_n_days_count(7),
                'sales_last_7_days_total': self._to_float(self.get_sales_last_n_days_total(7)),
                'inventory_movements_month': inventory_movements_month,
                'total_stock_units': self._to_int(total_stock_units),
                'total_products': total_products,
                'low_stock_count': low_stock_count,
                'best_month': {
                    'name': self.month_names[best_month_index] if best_month_value else 'Sin datos',
                    'value': self._to_float(best_month_value),
                },
                'top_product': top_product,
                'top_client': top_client,
            },
            'charts': {
                'sales_yearly': {
                    'categories': self.month_names,
                    'series': [
                        {
                            'name': 'Ventas {}'.format(year),
                            'data': monthly_totals,
                        },
                        {
                            'name': 'Ventas {}'.format(year - 1),
                            'data': previous_year_totals,
                        },
                    ],
                },
                'sales_daily': self.get_daily_totals(year, month),
                'top_products': self.get_top_products_chart(year, month),
                'top_clients': self.get_top_clients_chart(year, month),
            },
            'inventory': self.get_inventory_snapshot(),
        }

    def get_sales_last_n_days_queryset(self, n=7):
        end = timezone.localdate()
        start = end - timedelta(days=n - 1)
        return self.get_sales_queryset().filter(date_joined__range=(start, end))

    def get_sales_last_n_days_count(self, n=7):
        return self.get_sales_last_n_days_queryset(n).count()

    def get_sales_last_n_days_total(self, n=7):
        value = self.get_sales_last_n_days_queryset(n).aggregate(total_amount=Sum('total')).get('total_amount')
        return value or Decimal('0.00')

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST.get('action')
            year = self.get_selected_year(request.POST.get('year'))
            month = self.get_selected_month(request.POST.get('month'))

            if action == 'get_dashboard_overview':
                data = self.get_dashboard_overview(year, month)

            elif action == 'get_graph_sales_year_month':
                data = {
                    'name': f'Ventas {year}',
                    'showInLegend': False,
                    'colorByPoint': True,
                    'data': self.get_monthly_totals(year),
                }

            elif action == 'get_graph_sales_products_year_month':
                data = {
                    'name': 'Productos',
                    'colorByPoint': True,
                    'data': self.get_top_products_chart(year, month),
                }

            elif action == 'get_graph_sales_clients_year_month':
                data = self.get_top_clients_chart(year, month)

            elif action == 'get_graph_sales_daily':
                data = self.get_daily_totals(year, month)

            elif action == 'export_sales_csv':
                # Export sales for the selected year/month as CSV
                qs = self.get_sales_queryset().filter(date_joined__year=year, date_joined__month=month)
                filename = f"ventas_{year}_{str(month).zfill(2)}.csv"
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                writer = csv.writer(response)
                writer.writerow(['ID', 'Fecha', 'Cliente', 'Total', 'Profit', 'Estado', 'Notas'])
                for s in qs:
                    client = '{} {}'.format(s.cli.names or '', s.cli.surnames or '').strip() if getattr(s, 'cli', None) else ''
                    writer.writerow([
                        s.id,
                        s.date_joined.strftime('%Y-%m-%d'),
                        client,
                        str(s.total),
                        str(getattr(s, 'profit', '')),
                        getattr(s, 'status', ''),
                        getattr(s, 'observation', ''),
                    ])
                return response

            else:
                data = {'error': 'Acción no válida'}
        except Exception as e:
            data = {'error': str(e)}

        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.get_selected_year(self.request.GET.get('year'))
        month = self.get_selected_month(self.request.GET.get('month'))
        overview = self.get_dashboard_overview(year, month)

        context['title'] = 'Panel comercial'
        context['panel'] = 'Panel comercial'
        context['entity'] = 'Dashboard'
        context['list_url'] = reverse_lazy('erp:dashboard')
        context['dashboard_bootstrap'] = json.dumps(
            {
                'available_years': overview['filters']['available_years'],
                'initial_year': year,
                'initial_month': month,
                'initial_overview': overview,
            },
            cls=DjangoJSONEncoder,
        )
        return context
