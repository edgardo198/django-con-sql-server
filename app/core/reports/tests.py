from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app.core.erp.models import Client, Sale
from app.core.user.models import Organization


class ReportSaleViewTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name='Sucursal Centro', code='CENTRO')
        self.other_organization = Organization.objects.create(name='Sucursal Norte', code='NORTE')
        self.user = get_user_model().objects.create_user(
            username='reporter',
            password='secret123',
            is_superuser=True,
            is_staff=True,
        )
        self.user.organizations.add(self.organization, self.other_organization)
        self.user.current_organization = self.organization
        self.user.save(update_fields=['current_organization'])
        self.client.force_login(self.user)

        self.customer = Client.objects.create(
            organization=self.organization,
            names='Ana',
            surnames='Lopez',
            dni='0801199912345',
        )
        self.other_customer = Client.objects.create(
            organization=self.other_organization,
            names='Luis',
            surnames='Martinez',
            dni='0801199911111',
        )

    def test_custom_report_range_is_ordered_and_scoped(self):
        today = timezone.localdate()
        Sale.objects.create(
            organization=self.organization,
            cli=self.customer,
            date_joined=today,
            subtotal=Decimal('100.00'),
            tax_total=Decimal('15.00'),
            iva=Decimal('15.00'),
            total=Decimal('115.00'),
            profit=Decimal('20.00'),
        )
        Sale.objects.create(
            organization=self.other_organization,
            cli=self.other_customer,
            date_joined=today,
            subtotal=Decimal('200.00'),
            tax_total=Decimal('30.00'),
            iva=Decimal('30.00'),
            total=Decimal('230.00'),
            profit=Decimal('40.00'),
        )

        response = self.client.post(
            reverse('sale_report'),
            {
                'action': 'search_report',
                'period': 'custom',
                'start_date': today.strftime('%Y-%m-%d'),
                'end_date': today.replace(day=1).strftime('%Y-%m-%d'),
            },
        )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('error', payload)
        self.assertEqual(len(payload['rows']), 1)
        self.assertEqual(payload['summary']['tax_total'], 15.0)
        self.assertLessEqual(payload['start_date'], payload['end_date'])
        self.assertEqual(payload['top_clients'][0]['total'], 115.0)

    def test_default_month_uses_latest_sale_when_current_month_is_empty(self):
        first_day_this_month = timezone.localdate().replace(day=1)
        previous_month_date = first_day_this_month - timedelta(days=1)
        Sale.objects.create(
            organization=self.organization,
            cli=self.customer,
            date_joined=previous_month_date,
            subtotal=Decimal('100.00'),
            tax_total=Decimal('15.00'),
            iva=Decimal('15.00'),
            total=Decimal('115.00'),
            profit=Decimal('20.00'),
        )

        page_response = self.client.get(reverse('sale_report'))
        self.assertEqual(page_response.context['report_default_start_date'], previous_month_date.replace(day=1).strftime('%Y-%m-%d'))
        self.assertEqual(page_response.context['report_default_end_date'], previous_month_date.strftime('%Y-%m-%d'))

        data_response = self.client.post(
            reverse('sale_report'),
            {'action': 'search_report', 'period': 'month'},
        )

        payload = data_response.json()
        self.assertEqual(len(payload['rows']), 1)
        self.assertEqual(payload['summary']['total'], 115.0)
