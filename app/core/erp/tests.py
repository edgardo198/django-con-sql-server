import calendar
import io
import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.template.loader import get_template
from django.test import Client as DjangoClient, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from app.core.erp.models import (
    CashMovement,
    CashSession,
    Category,
    Client,
    DetPurchase,
    DetSale,
    FiscalData,
    InventoryMovement,
    Product,
    Purchase,
    Sale,
    Supplier,
    TaxRate,
)
from app.core.erp.views.dashboard.views import DashboardView
from app.core.user.access import ROLE_STORE_ADMIN
from app.core.user.models import Organization


class ERPDashboardAndReportsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.organization = Organization.objects.create(name='Sucursal Centro', code='CENTRO')
        self.secondary_organization = Organization.objects.create(name='Sucursal Norte', code='NORTE')

        self.user = get_user_model().objects.create_user(
            username='tester',
            password='secret123',
            first_name='Test',
            last_name='User',
            is_superuser=True,
            is_staff=True,
        )
        self.user.organizations.add(self.organization, self.secondary_organization)
        self.user.current_organization = self.organization
        self.user.save(update_fields=['current_organization'])

        self.client.force_login(self.user)

        self.category = Category.objects.create(name='Lacteos', organization=self.organization)
        self.customer = Client.objects.create(
            organization=self.organization,
            names='Ana',
            surnames='Lopez',
            dni='0801199912345',
        )
        self.product = Product.objects.create(
            organization=self.organization,
            name='Leche',
            cat=self.category,
            cost=Decimal('15.00'),
            pvp=Decimal('25.00'),
            stock=10,
            min_stock=2,
        )

        other_category = Category.objects.create(name='Bebidas', organization=self.secondary_organization)
        other_customer = Client.objects.create(
            organization=self.secondary_organization,
            names='Luis',
            surnames='Martinez',
            dni='0801199911111',
        )
        other_product = Product.objects.create(
            organization=self.secondary_organization,
            name='Jugo',
            cat=other_category,
            cost=Decimal('10.00'),
            pvp=Decimal('18.00'),
            stock=20,
            min_stock=5,
        )

        today = timezone.localdate()
        self.sale = Sale.objects.create(
            organization=self.organization,
            cli=self.customer,
            date_joined=today,
            iva=Decimal('3.75'),
        )
        DetSale.objects.create(
            sale=self.sale,
            prod=self.product,
            price=Decimal('25.00'),
            cost=Decimal('15.00'),
            cant=1,
        )
        self.sale.calculate_totals(iva=Decimal('3.75'))

        other_sale = Sale.objects.create(
            organization=self.secondary_organization,
            cli=other_customer,
            date_joined=today,
            iva=Decimal('2.70'),
        )
        DetSale.objects.create(
            sale=other_sale,
            prod=other_product,
            price=Decimal('18.00'),
            cost=Decimal('10.00'),
            cant=1,
        )
        other_sale.calculate_totals(iva=Decimal('2.70'))

    def test_dashboard_page_renders_bootstrap_data(self):
        response = self.client.get(reverse('erp:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_organization'].name, 'Sucursal Centro')
        bootstrap = json.loads(response.context['dashboard_bootstrap'])
        self.assertIn('initial_overview', bootstrap)
        self.assertEqual(bootstrap['initial_overview']['filters']['selected_month'], timezone.localdate().month)

    def test_dashboard_overview_filters_by_current_organization(self):
        response = self.client.post(
            reverse('erp:dashboard'),
            {
                'action': 'get_dashboard_overview',
                'year': timezone.localdate().year,
                'month': timezone.localdate().month,
            }
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['summary']['revenue_month'], 28.75)
        self.assertEqual(payload['summary']['top_product']['name'], 'Leche')
        self.assertEqual(payload['summary']['top_client']['name'], 'Ana Lopez')
        self.assertEqual(payload['summary']['total_products'], 1)
        self.assertEqual(payload['filters']['selected_organization'], 'Sucursal Centro')
        self.assertEqual(payload['inventory']['low_stock_products'], [])

    def test_dashboard_extra_graph_endpoints_return_expected_payloads(self):
        year = timezone.localdate().year
        month = timezone.localdate().month

        clients_response = self.client.post(
            reverse('erp:dashboard'),
            {
                'action': 'get_graph_sales_clients_year_month',
                'year': year,
                'month': month,
            }
        )
        self.assertEqual(clients_response.status_code, 200)
        clients_payload = clients_response.json()
        self.assertEqual(clients_payload['categories'], ['Ana Lopez'])
        self.assertEqual(clients_payload['series'][0]['data'][0]['sales_count'], 1)

        daily_response = self.client.post(
            reverse('erp:dashboard'),
            {
                'action': 'get_graph_sales_daily',
                'year': year,
                'month': month,
            }
        )
        self.assertEqual(daily_response.status_code, 200)
        daily_payload = daily_response.json()
        self.assertEqual(len(daily_payload['categories']), calendar.monthrange(year, month)[1])
        self.assertEqual(daily_payload['series'][0]['name'], 'Ventas diarias')

    def test_dashboard_yearly_series_has_twelve_months(self):
        request = self.factory.get(reverse('erp:dashboard'))
        request.user = self.user
        view = DashboardView()
        view.request = request

        year = timezone.localdate().year
        data = view.get_dashboard_overview(year, timezone.localdate().month)

        self.assertEqual(len(data['charts']['sales_yearly']['series'][0]['data']), 12)

    def test_report_view_returns_summary_for_active_organization(self):
        response = self.client.post(
            reverse('sale_report'),
            {
                'action': 'search_report',
                'start_date': timezone.localdate().strftime('%Y-%m-%d'),
                'end_date': timezone.localdate().strftime('%Y-%m-%d'),
            }
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload['rows']), 1)
        self.assertEqual(payload['rows'][0]['organization'], 'Sucursal Centro')
        self.assertEqual(payload['summary']['total'], 28.75)

    def test_report_page_defaults_to_current_month_range(self):
        response = self.client.get(reverse('sale_report'))

        today = timezone.localdate()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['report_default_start_date'], today.replace(day=1).strftime('%Y-%m-%d'))
        self.assertEqual(response.context['report_default_end_date'], today.strftime('%Y-%m-%d'))
        self.assertEqual(response.context['report_default_period'], 'month')
        self.assertContains(response, 'window.reportConfig')
        self.assertContains(response, 'data-period="day"')
        self.assertContains(response, 'data-period="week"')
        self.assertContains(response, 'data-period="month"')

    def test_report_endpoint_supports_day_week_and_month_periods(self):
        for period in ('day', 'week', 'month'):
            with self.subTest(period=period):
                response = self.client.post(
                    reverse('sale_report'),
                    {
                        'action': 'search_report',
                        'period': period,
                    },
                )

                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(len(payload['rows']), 1)
                self.assertEqual(payload['period'], period)
                self.assertIn('start_date', payload)
                self.assertIn('end_date', payload)

    def test_user_can_switch_current_organization(self):
        response = self.client.get(reverse('user:organization_switch', args=[self.secondary_organization.id]))

        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.current_organization_id, self.secondary_organization.id)

    def test_dashboard_recovers_when_current_organization_is_inactive(self):
        inactive_organization = Organization.objects.create(
            name='Sucursal Inactiva',
            code='INACTIVA',
            is_active=False,
        )
        self.user.current_organization = inactive_organization
        self.user.save(update_fields=['current_organization'])

        response = self.client.get(reverse('erp:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(response.context['current_organization'].id, self.organization.id)
        self.assertEqual(self.user.current_organization_id, self.organization.id)

    def test_organization_list_page_and_ajax_work(self):
        response = self.client.get(reverse('user:organization_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Listado de Tiendas')

        ajax_response = self.client.post(
            reverse('user:organization_list'),
            {'action': 'searchdata'},
        )
        self.assertEqual(ajax_response.status_code, 200)
        payload = ajax_response.json()
        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[0]['name'], 'Sucursal Centro')

    def test_sale_list_ajax_returns_only_active_store_sales(self):
        response = self.client.post(
            reverse('erp:sale_list'),
            {'action': 'searchdata'},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]['cli']['full_name'], 'Ana Lopez')
        self.assertEqual(payload[0]['organization'], self.organization.id)

    def test_sale_details_ajax_returns_details_for_selected_sale(self):
        response = self.client.post(
            reverse('erp:sale_list'),
            {'action': 'search_details_prod', 'id': self.sale.id},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]['prod']['name'], 'Leche')
        self.assertEqual(payload[0]['cant'], 1)

    def test_sale_create_renders_product_search_selector(self):
        response = self.client.get(reverse('erp:sale_create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'sale-product-search')
        self.assertContains(response, 'sale/js/form.js')

    def test_sale_product_search_returns_first_active_products_without_term(self):
        inactive_product = Product.objects.create(
            organization=self.organization,
            name='Producto Inactivo',
            cost=Decimal('8.00'),
            pvp=Decimal('14.00'),
            stock=5,
            is_active=False,
        )

        response = self.client.post(
            reverse('erp:sale_create'),
            {'action': 'search_products', 'term': ''},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        product_ids = [item['id'] for item in payload]
        self.assertEqual(product_ids, [self.product.id])
        self.assertNotIn(inactive_product.id, product_ids)

    def test_sale_product_search_requires_sale_permission(self):
        user_without_sale_perm = get_user_model().objects.create_user(
            username='sin_ventas',
            password='secret123',
        )
        user_without_sale_perm.organizations.add(self.organization)
        user_without_sale_perm.current_organization = self.organization
        user_without_sale_perm.save(update_fields=['current_organization'])
        self.client.force_login(user_without_sale_perm)

        get_response = self.client.get(reverse('erp:sale_create'))
        post_response = self.client.post(
            reverse('erp:sale_create'),
            {'action': 'search_products', 'term': ''},
        )

        self.assertEqual(get_response.status_code, 302)
        self.assertEqual(post_response.status_code, 302)

    def test_sale_product_search_works_with_csrf_enabled(self):
        client = DjangoClient(enforce_csrf_checks=True)
        client.force_login(self.user)
        get_response = client.get(reverse('erp:sale_create'))
        csrf_token = client.cookies['csrftoken'].value

        response = client.post(
            reverse('erp:sale_create'),
            {'action': 'search_products', 'term': ''},
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.json()], [self.product.id])

    def test_sale_create_works_with_csrf_enabled(self):
        client = DjangoClient(enforce_csrf_checks=True)
        client.force_login(self.user)
        get_response = client.get(reverse('erp:sale_create'))
        csrf_token = client.cookies['csrftoken'].value
        payload = {
            'cli': self.customer.id,
            'cash_session': '',
            'document_type': 'receipt',
            'payment_term': 'cash',
            'date_joined': timezone.localdate().strftime('%Y-%m-%d'),
            'due_date': '',
            'discount': '0.00',
            'amount_paid': '0.00',
            'observation': 'Venta con csrf QA',
            'products': [
                {'id': self.product.id, 'cant': 1, 'price': '25.00', 'cost': '15.00', 'discount': '0.00'},
            ],
        }

        response = client.post(
            reverse('erp:sale_create'),
            {'action': 'add', 'sale': json.dumps(payload)},
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('error', response.json())
        self.assertTrue(Sale.objects.filter(organization=self.organization, observation='Venta con csrf QA').exists())

    def test_sale_update_legacy_payload_keeps_stock_until_confirmation(self):
        response = self.client.post(
            reverse('erp:sale_update', args=[self.sale.id]),
            {
                'action': 'edit',
                'vents': json.dumps({
                    'cli': self.customer.id,
                    'date_joined': timezone.localdate().strftime('%Y-%m-%d'),
                    'iva': '5.00',
                    'observation': 'Venta actualizada',
                    'products': [
                        {
                            'id': self.product.id,
                            'cant': 2,
                            'price': '25.00',
                            'pvp': '25.00',
                            'cost': '15.00',
                        }
                    ],
                }),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.sale.refresh_from_db()

        self.assertEqual(self.product.stock, 10)
        self.assertEqual(self.sale.subtotal, Decimal('50.00'))
        self.assertEqual(self.sale.iva, Decimal('5.00'))
        self.assertEqual(self.sale.total, Decimal('55.00'))

    def test_sale_delete_restores_stock(self):
        response = self.client.post(reverse('erp:sale_delete', args=[self.sale.id]))

        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()

        self.assertFalse(Sale.objects.filter(pk=self.sale.id).exists())
        self.assertEqual(self.product.stock, 10)

    def test_organization_delete_with_related_data_deactivates_instead_of_removing(self):
        self.client.get(reverse('user:organization_switch', args=[self.secondary_organization.id]))

        response = self.client.post(reverse('user:organization_delete', args=[self.organization.id]))

        self.assertEqual(response.status_code, 200)
        self.organization.refresh_from_db()
        self.assertFalse(self.organization.is_active)
        self.assertTrue(Organization.objects.filter(pk=self.organization.id).exists())

    def test_navigation_pages_render_for_admin_flow(self):
        urls = [
            reverse('erp:dashboard'),
            reverse('sale_report'),
            reverse('user:organization_list'),
            reverse('user:user_list'),
            reverse('erp:category_list'),
            reverse('erp:product_list'),
            reverse('erp:client_list'),
            reverse('erp:sale_list'),
            reverse('erp:sale_create'),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_namespaced_urls_resolve_for_multistore_navigation(self):
        self.assertEqual(reverse('user:organization_list'), '/user/organization/list/')
        self.assertEqual(reverse('user:organization_switch', args=[self.organization.id]), '/user/organization/switch/{}/'.format(self.organization.id))
        self.assertEqual(reverse('organization_list'), '/user/organization/list/')
        self.assertEqual(reverse('organization_switch', args=[self.organization.id]), '/user/organization/switch/{}/'.format(self.organization.id))
        self.assertEqual(reverse('erp:supplier_list'), '/erp/supplier/list/')
        self.assertEqual(reverse('supplier_list'), '/erp/supplier/list/')

    def test_dashboard_renders_multistore_sidebar_link(self):
        response = self.client.get(reverse('erp:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('user:organization_list'))

    def test_new_erp_navigation_pages_render_for_admin_flow(self):
        urls = [
            reverse('erp:supplier_list'),
            reverse('erp:supplier_create'),
            reverse('erp:taxrate_list'),
            reverse('erp:taxrate_create'),
            reverse('erp:fiscaldata_manage'),
            reverse('erp:cashsession_list'),
            reverse('erp:cashsession_create'),
            reverse('erp:cashmovement_list'),
            reverse('erp:cashmovement_create'),
            reverse('erp:inventorymovement_list'),
            reverse('erp:purchase_list'),
            reverse('erp:purchase_create'),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url, follow=True)
                self.assertEqual(response.status_code, 200)

    def test_object_action_pages_render_for_current_store(self):
        supplier = Supplier.objects.create(organization=self.organization, name='Proveedor Acciones')
        tax_rate = TaxRate.objects.create(
            organization=self.organization,
            name='ISV Acciones',
            code='ACT15',
            rate=Decimal('15.00'),
        )
        fiscal_data = FiscalData.objects.create(
            organization=self.organization,
            business_name='Empresa Acciones',
            rtn='08011999123456',
            address='Direccion fiscal',
        )
        cash_session = CashSession.objects.create(
            organization=self.organization,
            user=self.user,
            opening_amount=Decimal('100.00'),
        )
        cash_movement = CashMovement.objects.create(
            organization=self.organization,
            cash_session=cash_session,
            movement_type='income',
            amount=Decimal('10.00'),
            description='Ingreso acciones',
        )
        purchase = Purchase.objects.create(
            organization=self.organization,
            supplier=supplier,
            number='ACT-PUR-001',
        )

        urls = [
            reverse('erp:category_update', args=[self.category.id]),
            reverse('erp:category_delete', args=[self.category.id]),
            reverse('erp:client_update', args=[self.customer.id]),
            reverse('erp:client_delete', args=[self.customer.id]),
            reverse('erp:product_update', args=[self.product.id]),
            reverse('erp:product_delete', args=[self.product.id]),
            reverse('erp:supplier_update', args=[supplier.id]),
            reverse('erp:supplier_delete', args=[supplier.id]),
            reverse('erp:taxrate_update', args=[tax_rate.id]),
            reverse('erp:taxrate_delete', args=[tax_rate.id]),
            reverse('erp:fiscaldata_update', args=[fiscal_data.id]),
            reverse('erp:cashsession_close', args=[cash_session.id]),
            reverse('erp:cashmovement_delete', args=[cash_movement.id]),
            reverse('erp:purchase_update', args=[purchase.id]),
            reverse('erp:purchase_delete', args=[purchase.id]),
            reverse('erp:purchase_confirm', args=[purchase.id]),
            reverse('erp:purchase_cancel', args=[purchase.id]),
            reverse('erp:sale_update', args=[self.sale.id]),
            reverse('erp:sale_delete', args=[self.sale.id]),
            reverse('erp:sale_confirm', args=[self.sale.id]),
            reverse('erp:sale_cancel', args=[self.sale.id]),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_purchase_recalculate_totals_keeps_iva_in_sync(self):
        supplier = Supplier.objects.create(
            organization=self.organization,
            name='Proveedor Centro',
        )
        tax_rate = TaxRate.objects.create(
            organization=self.organization,
            name='ISV 15',
            code='ISV15',
            rate=Decimal('15.00'),
        )
        self.product.tax_rate = tax_rate
        self.product.save(update_fields=['tax_rate'])
        purchase = Purchase.objects.create(
            organization=self.organization,
            supplier=supplier,
        )

        DetPurchase.objects.create(
            purchase=purchase,
            prod=self.product,
            cost=Decimal('100.00'),
            cant=2,
        )

        purchase.refresh_from_db()
        self.assertEqual(purchase.subtotal, Decimal('200.00'))
        self.assertEqual(purchase.tax_total, Decimal('30.00'))
        self.assertEqual(purchase.iva, Decimal('30.00'))
        self.assertEqual(purchase.total, Decimal('230.00'))

    def test_product_json_is_safe_without_category(self):
        product = Product.objects.create(
            organization=self.organization,
            name='Servicio sin categoria',
            cost=Decimal('0.00'),
            pvp=Decimal('50.00'),
            stock=0,
            min_stock=0,
            is_service=True,
        )

        payload = product.toJSON()
        self.assertEqual(payload['cat']['name'], 'Sin categoria')

    def test_product_without_tax_rate_uses_default_15_percent(self):
        payload = self.product.toJSON()
        self.assertEqual(payload['tax_rate'], '15.00')

        sale = Sale.objects.create(
            organization=self.organization,
            cli=self.customer,
            date_joined=timezone.localdate(),
        )
        DetSale.objects.create(
            sale=sale,
            prod=self.product,
            price=Decimal('100.00'),
            cost=Decimal('60.00'),
            cant=2,
        )

        sale.refresh_from_db()
        self.assertEqual(sale.subtotal, Decimal('200.00'))
        self.assertEqual(sale.tax_total, Decimal('30.00'))
        self.assertEqual(sale.total, Decimal('230.00'))

    def test_sale_invoice_template_renders_current_detail_relation(self):
        template = get_template('sale/invoice.html')
        html = template.render({
            'sale': self.sale,
            'comp': {
                'name': self.organization.name,
                'ruc': self.organization.rtn or 'N/D',
                'address': self.organization.address or 'N/D',
            },
            'icon': '',
        })

        self.assertIn('Leche', html)
        self.assertIn('Lacteos', html)

    def test_sale_create_can_add_client_from_modal_action(self):
        response = self.client.post(
            reverse('erp:sale_create'),
            {
                'action': 'create_client',
                'names': 'Mario',
                'surnames': 'Rivera',
                'dni': '0801199913333',
                'rtn': '',
                'date_birthday': '',
                'address': 'Barrio Centro',
                'phone': '9999-3333',
                'email': 'mario.rivera@example.com',
                'gender': 'male',
                'credit_limit': '0.00',
                'is_active': 'on',
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertNotIn('error', payload)
        self.assertEqual(payload['text'], 'Mario Rivera')
        self.assertTrue(Client.objects.filter(organization=self.organization, id=payload['id']).exists())

    def test_create_qa_profile_command_builds_manual_testing_profile(self):
        stdout = io.StringIO()
        call_command(
            'create_qa_profile',
            username='qa_full',
            password='QaPass123!',
            email='qa_full@example.com',
            store_name='Tienda QA Full',
            stdout=stdout,
        )

        qa_user = get_user_model().objects.get(username='qa_full')
        qa_organization = Organization.objects.get(name='Tienda QA Full')

        self.assertTrue(qa_user.check_password('QaPass123!'))
        self.assertEqual(qa_user.current_organization, qa_organization)
        self.assertTrue(qa_user.groups.filter(name=ROLE_STORE_ADMIN).exists())
        self.assertTrue(Category.objects.filter(organization=qa_organization, name='Categoria QA').exists())
        self.assertTrue(Supplier.objects.filter(organization=qa_organization, name='Proveedor QA').exists())
        self.assertTrue(TaxRate.objects.filter(organization=qa_organization, code='QA15').exists())
        self.assertTrue(Client.objects.filter(organization=qa_organization, dni='0801199912345').exists())
        self.assertTrue(Product.objects.filter(organization=qa_organization, barcode='QA-0001').exists())
        self.assertTrue(FiscalData.objects.filter(organization=qa_organization).exists())
        self.assertTrue(CashSession.objects.filter(organization=qa_organization, status='open').exists())

    def test_catalog_pages_support_full_crud_cycle(self):
        category_response = self.client.post(
            reverse('erp:category_create'),
            {'action': 'add', 'name': 'Panaderia', 'description': 'Pan fresco', 'desc': '', 'is_active': 'on'},
        )
        self.assertEqual(category_response.status_code, 200)
        self.assertNotIn('error', category_response.json())
        category = Category.objects.get(organization=self.organization, name='Panaderia')

        category_update = self.client.post(
            reverse('erp:category_update', args=[category.id]),
            {'action': 'edit', 'name': 'Panaderia Editada', 'description': 'Pan diario', 'desc': '', 'is_active': 'on'},
        )
        self.assertEqual(category_update.status_code, 200)
        category.refresh_from_db()
        self.assertEqual(category.name, 'Panaderia Editada')
        self.assertEqual(category.desc, 'Pan diario')

        supplier_response = self.client.post(
            reverse('erp:supplier_create'),
            {
                'name': 'Proveedor CRUD',
                'rtn': '08011999123456',
                'contact_name': 'Contacto CRUD',
                'phone': '2222-7777',
                'email': 'crud@example.com',
                'address': 'Direccion CRUD',
                'is_active': 'on',
            },
        )
        self.assertEqual(supplier_response.status_code, 200)
        self.assertNotIn('error', supplier_response.json())
        supplier = Supplier.objects.get(organization=self.organization, name='Proveedor CRUD')

        supplier_update = self.client.post(
            reverse('erp:supplier_update', args=[supplier.id]),
            {
                'name': 'Proveedor CRUD Editado',
                'rtn': '08011999123456',
                'contact_name': 'Contacto Editado',
                'phone': '2222-8888',
                'email': 'crud-editado@example.com',
                'address': 'Direccion editada',
                'is_active': 'on',
            },
        )
        self.assertEqual(supplier_update.status_code, 200)
        supplier.refresh_from_db()
        self.assertEqual(supplier.name, 'Proveedor CRUD Editado')

        tax_response = self.client.post(
            reverse('erp:taxrate_create'),
            {'name': 'ISV CRUD', 'rate': '12.00', 'code': 'CRUD12', 'is_default': 'on', 'is_active': 'on'},
        )
        self.assertEqual(tax_response.status_code, 200)
        self.assertNotIn('error', tax_response.json())
        tax_rate = TaxRate.objects.get(organization=self.organization, code='CRUD12')
        self.assertTrue(tax_rate.is_default)

        client_response = self.client.post(
            reverse('erp:client_create'),
            {
                'action': 'add',
                'names': 'Cliente',
                'surnames': 'CRUD',
                'dni': '0801199912222',
                'rtn': '08011999122223',
                'date_birthday': '1995-01-01',
                'address': 'Direccion cliente',
                'phone': '2222-9999',
                'email': 'cliente-crud@example.com',
                'gender': 'other',
                'credit_limit': '250.00',
                'is_credit_customer': 'on',
                'is_active': 'on',
            },
        )
        self.assertEqual(client_response.status_code, 200)
        self.assertNotIn('error', client_response.json())
        created_client = Client.objects.get(organization=self.organization, dni='0801199912222')
        self.assertTrue(created_client.is_credit_customer)

        product_response = self.client.post(
            reverse('erp:product_create'),
            {
                'action': 'add',
                'name': 'Producto CRUD',
                'category': category.id,
                'cat': category.id,
                'barcode': 'CRUD-001',
                'internal_code': 'CRUD-INT-001',
                'description': 'Producto CRUD',
                'unit': 'unidad',
                'cost': '10.00',
                'pvp': '15.00',
                'stock': '5',
                'min_stock': '1',
                'tax_rate': tax_rate.id,
                'is_active': 'on',
            },
        )
        self.assertEqual(product_response.status_code, 200)
        self.assertNotIn('error', product_response.json())
        product = Product.objects.get(organization=self.organization, barcode='CRUD-001')
        self.assertEqual(product.category_id, category.id)
        self.assertEqual(product.cat_id, category.id)

    def test_cash_pages_support_open_movement_and_close_cycle(self):
        open_response = self.client.post(
            reverse('erp:cashsession_create'),
            {'opening_amount': '150.00', 'notes': 'Apertura prueba'},
        )
        self.assertEqual(open_response.status_code, 200)
        self.assertNotIn('error', open_response.json())
        cash_session = CashSession.objects.filter(
            organization=self.organization,
            user=self.user,
            opening_amount=Decimal('150.00'),
        ).latest('id')

        movement_response = self.client.post(
            reverse('erp:cashmovement_create'),
            {
                'cash_session': cash_session.id,
                'movement_type': 'income',
                'amount': '25.00',
                'description': 'Ingreso de prueba',
                'reference': 'QA-CASH-001',
            },
        )
        self.assertEqual(movement_response.status_code, 200)
        self.assertNotIn('error', movement_response.json())
        self.assertTrue(CashMovement.objects.filter(cash_session=cash_session, reference='QA-CASH-001').exists())

        cash_session.refresh_from_db()
        self.assertEqual(cash_session.expected_amount, Decimal('175.00'))

        close_response = self.client.post(
            reverse('erp:cashsession_close', args=[cash_session.id]),
            {'closing_amount': '175.00', 'notes': 'Cierre cuadrado'},
        )
        self.assertEqual(close_response.status_code, 200)
        self.assertNotIn('error', close_response.json())
        cash_session.refresh_from_db()
        self.assertEqual(cash_session.status, 'closed')
        self.assertEqual(cash_session.difference, Decimal('0.00'))

    def test_purchase_pages_support_create_confirm_and_cancel_cycle(self):
        supplier = Supplier.objects.create(organization=self.organization, name='Proveedor Compra QA')
        tax_rate = TaxRate.objects.create(organization=self.organization, name='ISV Compra QA', code='PUR15', rate=Decimal('15.00'))
        self.product.tax_rate = tax_rate
        self.product.save(update_fields=['tax_rate'])
        starting_stock = self.product.stock

        payload = {
            'supplier': supplier.id,
            'number': 'PUR-QA-001',
            'supplier_invoice': 'FAC-QA-001',
            'payment_term': 'cash',
            'date_joined': timezone.localdate().strftime('%Y-%m-%d'),
            'due_date': '',
            'amount_paid': '0.00',
            'observation': 'Compra QA',
            'products': [
                {'id': self.product.id, 'cant': 3, 'cost': '12.00'},
            ],
        }
        create_response = self.client.post(
            reverse('erp:purchase_create'),
            {'action': 'add', 'purchase': json.dumps(payload)},
        )
        self.assertEqual(create_response.status_code, 200)
        self.assertNotIn('error', create_response.json())
        purchase = Purchase.objects.get(organization=self.organization, number='PUR-QA-001')
        self.assertEqual(purchase.status, 'draft')
        self.assertEqual(purchase.total, Decimal('41.40'))

        confirm_response = self.client.post(reverse('erp:purchase_confirm', args=[purchase.id]))
        self.assertEqual(confirm_response.status_code, 200)
        self.assertNotIn('error', confirm_response.json())
        purchase.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(purchase.status, 'confirmed')
        self.assertEqual(self.product.stock, starting_stock + 3)
        self.assertTrue(InventoryMovement.objects.filter(reference=f'PUR-{purchase.id}', movement_type='purchase').exists())

        cancel_response = self.client.post(
            reverse('erp:purchase_cancel', args=[purchase.id]),
            {'reason': 'Prueba de anulacion'},
        )
        self.assertEqual(cancel_response.status_code, 200)
        self.assertNotIn('error', cancel_response.json())
        purchase.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(purchase.status, 'cancelled')
        self.assertEqual(self.product.stock, starting_stock)

    def test_purchase_create_returns_clear_error_when_supplier_is_missing(self):
        payload = {
            'supplier': '',
            'number': 'PUR-SIN-PROV',
            'supplier_invoice': 'FAC-SIN-PROV',
            'payment_term': 'cash',
            'date_joined': timezone.localdate().strftime('%Y-%m-%d'),
            'due_date': '',
            'amount_paid': '0.00',
            'observation': 'Compra sin proveedor',
            'products': [
                {'id': self.product.id, 'cant': 1, 'cost': '12.00'},
            ],
        }

        response = self.client.post(
            reverse('erp:purchase_create'),
            {'action': 'add', 'purchase': json.dumps(payload)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()['error'],
            'Debe seleccionar un proveedor antes de registrar la compra.',
        )

    def test_purchase_create_returns_clear_error_when_product_id_is_missing(self):
        supplier = Supplier.objects.create(organization=self.organization, name='Proveedor sin producto QA')
        payload = {
            'supplier': supplier.id,
            'number': 'PUR-SIN-PROD',
            'supplier_invoice': 'FAC-SIN-PROD',
            'payment_term': 'cash',
            'date_joined': timezone.localdate().strftime('%Y-%m-%d'),
            'due_date': '',
            'amount_paid': '0.00',
            'observation': 'Compra con producto invalido',
            'products': [
                {'id': '', 'cant': 1, 'cost': '12.00'},
            ],
        }

        response = self.client.post(
            reverse('erp:purchase_create'),
            {'action': 'add', 'purchase': json.dumps(payload)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()['error'],
            'Hay un producto sin identificador valido en el detalle.',
        )

    def test_purchase_product_search_is_scoped_and_accepts_flexible_terms(self):
        self.product.name = 'Leche Entera Premium 1 Litro'
        self.product.barcode = 'BAR-LECHE-001'
        self.product.internal_code = 'LACT-001'
        self.product.description = 'Producto lacteo refrigerado'
        self.product.save(update_fields=['name', 'barcode', 'internal_code', 'description'])

        Product.objects.create(
            organization=self.secondary_organization,
            name='Leche Entera Norte',
            barcode='BAR-LECHE-002',
            internal_code='LACT-002',
            cost=Decimal('12.00'),
            pvp=Decimal('22.00'),
            stock=8,
        )

        response = self.client.post(
            reverse('erp:purchase_create'),
            {'action': 'search_products', 'term': '  leche litro  '},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]['id'], self.product.id)
        self.assertEqual(payload[0]['text'], 'Leche Entera Premium 1 Litro')

    def test_purchase_product_search_accepts_q_parameter_and_codes(self):
        self.product.barcode = '750-XYZ-001'
        self.product.internal_code = 'INT-LECHE-77'
        self.product.description = 'Bebida para cafeteria'
        self.product.save(update_fields=['barcode', 'internal_code', 'description'])

        barcode_response = self.client.post(
            reverse('erp:purchase_create'),
            {'action': 'search_products', 'q': '750-XYZ'},
        )
        internal_code_response = self.client.post(
            reverse('erp:purchase_create'),
            {'action': 'search_products', 'q': 'INT-LECHE'},
        )
        description_response = self.client.post(
            reverse('erp:purchase_create'),
            {'action': 'search_products', 'q': 'cafeteria'},
        )

        self.assertEqual([item['id'] for item in barcode_response.json()], [self.product.id])
        self.assertEqual([item['id'] for item in internal_code_response.json()], [self.product.id])
        self.assertEqual([item['id'] for item in description_response.json()], [self.product.id])

    def test_sale_create_returns_clear_error_when_client_is_missing(self):
        payload = {
            'cli': '',
            'cash_session': '',
            'document_type': 'receipt',
            'payment_term': 'cash',
            'date_joined': timezone.localdate().strftime('%Y-%m-%d'),
            'due_date': '',
            'discount': '0.00',
            'amount_paid': '0.00',
            'observation': 'Venta sin cliente',
            'products': [
                {'id': self.product.id, 'cant': 1, 'price': '25.00', 'cost': '15.00', 'discount': '0.00'},
            ],
        }

        response = self.client.post(
            reverse('erp:sale_create'),
            {'action': 'add', 'sale': json.dumps(payload)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()['error'],
            'Debe seleccionar un cliente antes de registrar la venta.',
        )

    def test_sale_product_search_is_scoped_and_accepts_flexible_terms(self):
        self.product.name = 'Leche Entera Premium 1 Litro'
        self.product.barcode = 'BAR-LECHE-001'
        self.product.internal_code = 'LACT-001'
        self.product.description = 'Producto lacteo refrigerado'
        self.product.save(update_fields=['name', 'barcode', 'internal_code', 'description'])

        Product.objects.create(
            organization=self.secondary_organization,
            name='Leche Entera Norte',
            barcode='BAR-LECHE-002',
            internal_code='LACT-002',
            cost=Decimal('12.00'),
            pvp=Decimal('22.00'),
            stock=8,
        )

        response = self.client.post(
            reverse('erp:sale_create'),
            {'action': 'search_products', 'term': '  leche litro  '},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]['id'], self.product.id)
        self.assertEqual(payload[0]['text'], 'Leche Entera Premium 1 Litro')

    def test_sale_product_search_finds_codes_and_description(self):
        self.product.barcode = '750-XYZ-001'
        self.product.internal_code = 'INT-LECHE-77'
        self.product.description = 'Bebida para cafeteria'
        self.product.save(update_fields=['barcode', 'internal_code', 'description'])

        barcode_response = self.client.post(
            reverse('erp:sale_create'),
            {'action': 'search_products', 'term': '750-XYZ'},
        )
        internal_code_response = self.client.post(
            reverse('erp:sale_create'),
            {'action': 'search_products', 'term': 'INT-LECHE'},
        )
        description_response = self.client.post(
            reverse('erp:sale_create'),
            {'action': 'search_products', 'term': 'cafeteria'},
        )
        category_response = self.client.post(
            reverse('erp:sale_create'),
            {'action': 'search_products', 'term': 'Lacteos'},
        )

        self.assertEqual([item['id'] for item in barcode_response.json()], [self.product.id])
        self.assertEqual([item['id'] for item in internal_code_response.json()], [self.product.id])
        self.assertEqual([item['id'] for item in description_response.json()], [self.product.id])
        self.assertEqual([item['id'] for item in category_response.json()], [self.product.id])

    def test_sale_pages_support_create_confirm_invoice_and_cancel_cycle(self):
        FiscalData.objects.update_or_create(
            organization=self.organization,
            defaults={
                'business_name': 'Empresa Test',
                'trade_name': 'Test',
                'rtn': '08011999123456',
                'address': 'Direccion fiscal',
                'cai': 'CAI-TEST',
                'cai_start_date': timezone.localdate(),
                'cai_end_date': timezone.localdate() + timedelta(days=30),
                'invoice_prefix': '001-001-01-',
                'invoice_range_start': 1,
                'invoice_range_end': 99999999,
                'next_invoice_number': 1,
            },
        )
        tax_rate = TaxRate.objects.create(organization=self.organization, name='ISV Venta QA', code='SAL15', rate=Decimal('15.00'))
        self.product.tax_rate = tax_rate
        self.product.stock = 10
        self.product.save(update_fields=['tax_rate', 'stock'])

        payload = {
            'cli': self.customer.id,
            'cash_session': '',
            'document_type': 'invoice',
            'payment_term': 'cash',
            'date_joined': timezone.localdate().strftime('%Y-%m-%d'),
            'due_date': '',
            'discount': '0.00',
            'amount_paid': '0.00',
            'observation': 'Venta QA',
            'products': [
                {'id': self.product.id, 'cant': 2, 'price': '25.00', 'cost': '15.00', 'discount': '0.00'},
            ],
        }
        create_response = self.client.post(
            reverse('erp:sale_create'),
            {'action': 'add', 'sale': json.dumps(payload)},
        )
        self.assertEqual(create_response.status_code, 200)
        self.assertNotIn('error', create_response.json())
        sale = Sale.objects.filter(organization=self.organization, observation='Venta QA').latest('id')
        self.assertEqual(sale.status, 'draft')
        self.assertEqual(sale.total, Decimal('57.50'))

        confirm_response = self.client.post(reverse('erp:sale_confirm', args=[sale.id]))
        self.assertEqual(confirm_response.status_code, 200)
        self.assertNotIn('error', confirm_response.json())
        sale.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(sale.status, 'confirmed')
        self.assertTrue(sale.number.startswith('001-001-01-'))
        self.assertEqual(self.product.stock, 8)

        invoice_response = self.client.get(reverse('erp:sale_invoice_pdf', args=[sale.id]))
        self.assertEqual(invoice_response.status_code, 200)
        self.assertEqual(invoice_response['Content-Type'], 'application/pdf')

        cancel_response = self.client.post(
            reverse('erp:sale_cancel', args=[sale.id]),
            {'reason': 'Prueba de anulacion'},
        )
        self.assertEqual(cancel_response.status_code, 200)
        self.assertNotIn('error', cancel_response.json())
        sale.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(sale.status, 'cancelled')
        self.assertEqual(self.product.stock, 10)

    def test_sale_save_and_print_returns_thermal_ticket_url(self):
        FiscalData.objects.update_or_create(
            organization=self.organization,
            defaults={
                'business_name': 'Empresa Ticket',
                'trade_name': 'Ticket Store',
                'rtn': '08011999123456',
                'address': 'Direccion fiscal',
                'cai': 'CAI-TICKET',
                'cai_start_date': timezone.localdate(),
                'cai_end_date': timezone.localdate() + timedelta(days=30),
                'invoice_prefix': '001-002-01-',
                'invoice_range_start': 1,
                'invoice_range_end': 99999999,
                'next_invoice_number': 1,
            },
        )
        self.product.stock = 10
        self.product.tax_rate = None
        self.product.save(update_fields=['stock', 'tax_rate'])

        payload = {
            'cli': self.customer.id,
            'cash_session': '',
            'document_type': 'invoice',
            'payment_term': 'cash',
            'date_joined': timezone.localdate().strftime('%Y-%m-%d'),
            'due_date': '',
            'discount': '0.00',
            'amount_paid': '115.00',
            'observation': 'Venta ticket QA',
            'products': [
                {'id': self.product.id, 'cant': 1, 'price': '100.00', 'cost': '60.00', 'discount': '0.00'},
            ],
        }
        response = self.client.post(
            reverse('erp:sale_create'),
            {
                'action': 'add',
                'sale': json.dumps(payload),
                'print_after_save': '1',
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertNotIn('error', data)
        self.assertIn('print_url', data)

        sale = Sale.objects.get(pk=data['id'])
        self.assertEqual(sale.status, 'confirmed')
        self.assertEqual(sale.tax_total, Decimal('15.00'))
        self.assertEqual(sale.total, Decimal('115.00'))

        ticket_response = self.client.get(data['print_url'])
        self.assertEqual(ticket_response.status_code, 200)
        self.assertContains(ticket_response, 'Gracias por su compra')

    def test_sale_save_and_print_keeps_draft_when_confirmation_fails(self):
        payload = {
            'cli': self.customer.id,
            'cash_session': '',
            'document_type': 'invoice',
            'payment_term': 'cash',
            'date_joined': timezone.localdate().strftime('%Y-%m-%d'),
            'due_date': '',
            'discount': '0.00',
            'amount_paid': '25.00',
            'observation': 'Venta sin datos fiscales QA',
            'products': [
                {'id': self.product.id, 'cant': 1, 'price': '25.00', 'cost': '15.00', 'discount': '0.00'},
            ],
        }

        response = self.client.post(
            reverse('erp:sale_create'),
            {
                'action': 'add',
                'sale': json.dumps(payload),
                'print_after_save': '1',
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertNotIn('error', data)
        self.assertIn('warning', data)
        sale = Sale.objects.get(pk=data['id'])
        self.assertEqual(sale.status, 'draft')
        self.assertEqual(sale.observation, 'Venta sin datos fiscales QA')
