import os
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from app.core.erp.models import Category, Client, Product, Sale
from app.core.sync.models import SyncOutbox
from app.core.sync.serializers import apply_record, collect_pull_records
from app.core.sync.services import (
    get_configured_remote_url,
    get_configured_sync_token,
    set_remote_sync_enabled,
    update_sync_connection,
)
from app.core.user.models import Organization


class SyncDirectionTests(TestCase):
    def create_sale_data(self):
        organization = Organization.objects.create(name='Centro', code='CENTRO')
        category = Category.objects.create(organization=organization, name='General')
        product = Product.objects.create(
            organization=organization,
            category=category,
            name='Cafe',
            pvp=25,
            stock=0,
        )
        client = Client.objects.create(
            organization=organization,
            names='Consumidor',
            surnames='Final',
        )
        sale = Sale.objects.create(
            organization=organization,
            cli=client,
            total=25,
            amount_paid=25,
            balance=0,
            status='confirmed',
        )
        return {
            'organization': organization,
            'category': category,
            'product': product,
            'client': client,
            'sale': sale,
        }

    def test_local_node_queues_only_sales_movements_and_clients(self):
        with patch.dict(os.environ, {'SYNC_NODE_ROLE': 'local'}):
            self.create_sale_data()

        labels = set(SyncOutbox.objects.values_list('model_label', flat=True))
        self.assertIn('erp.client', labels)
        self.assertIn('erp.sale', labels)
        self.assertNotIn('erp.product', labels)
        self.assertNotIn('erp.category', labels)
        self.assertNotIn('user.organization', labels)

    def test_central_node_queues_catalog_config_and_clients_only(self):
        with patch.dict(os.environ, {'SYNC_NODE_ROLE': 'central'}):
            self.create_sale_data()

        labels = set(SyncOutbox.objects.values_list('model_label', flat=True))
        self.assertIn('user.organization', labels)
        self.assertIn('erp.category', labels)
        self.assertIn('erp.product', labels)
        self.assertIn('erp.client', labels)
        self.assertNotIn('erp.sale', labels)

    def test_collect_pull_records_uses_current_node_outgoing_direction(self):
        with patch.dict(os.environ, {'SYNC_NODE_ROLE': 'local'}):
            self.create_sale_data()
            local_records, _, _ = collect_pull_records()

        with patch.dict(os.environ, {'SYNC_NODE_ROLE': 'central'}):
            central_records, _, _ = collect_pull_records()

        local_models = {record['model'] for record in local_records}
        central_models = {record['model'] for record in central_records}

        self.assertIn('erp.sale', local_models)
        self.assertIn('erp.client', local_models)
        self.assertNotIn('erp.product', local_models)

        self.assertIn('erp.product', central_models)
        self.assertIn('erp.client', central_models)
        self.assertNotIn('erp.sale', central_models)

    def test_apply_record_ignores_models_not_allowed_for_current_node(self):
        with patch.dict(os.environ, {'SYNC_NODE_ROLE': 'local'}):
            result = apply_record({
                'model': 'erp.sale',
                'sync_uuid': '11111111-1111-1111-1111-111111111111',
                'deleted': False,
                'updated_at': None,
                'fields': {},
                'm2m': {},
            })

        self.assertEqual(result['status'], 'ignored')
        self.assertIn('no permitido', result['reason'])

    def test_pending_count_filters_by_direction(self):
        with patch.dict(os.environ, {'SYNC_NODE_ROLE': 'central'}):
            self.create_sale_data()
            set_remote_sync_enabled(True)

            output = StringIO()
            call_command('sync_pending_count', stdout=output)

        self.assertEqual(output.getvalue().strip(), '4')

    def test_pending_count_returns_zero_when_sync_is_paused(self):
        with patch.dict(os.environ, {'SYNC_NODE_ROLE': 'central'}):
            self.create_sale_data()
            set_remote_sync_enabled(False)

            output = StringIO()
            call_command('sync_pending_count', stdout=output)

        self.assertEqual(output.getvalue().strip(), '0')


class SyncPanelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='admin',
            password='admin12345',
            email='admin@example.com',
        )
        set_remote_sync_enabled(True, self.user)
        self.client.force_login(self.user)

    def test_panel_renders_status_and_sync_now_button(self):
        with patch.dict(os.environ, {'SYNC_NODE_ROLE': 'local'}):
            response = self.client.get(reverse('sync:panel'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Estado de sincronizacion')
        self.assertContains(response, 'Caja local')
        self.assertContains(response, 'Desactivar sincronizacion')
        self.assertContains(response, 'Guardar conexion')
        self.assertContains(response, 'Sincronizar ahora')

    def test_panel_saves_render_connection_without_exposing_token(self):
        response = self.client.post(
            reverse('sync:panel'),
            {
                'action': 'save_connection',
                'remote_url': 'https://tienda-demo.onrender.com/',
                'sync_token': 'secret-token',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Conexion de Render guardada correctamente')
        self.assertEqual(get_configured_remote_url(), 'https://tienda-demo.onrender.com')
        self.assertEqual(get_configured_sync_token(), 'secret-token')
        self.assertNotContains(response, 'secret-token')

    def test_panel_requires_token_when_saving_first_connection(self):
        with patch.dict(os.environ, {'SYNC_API_TOKEN': '', 'DJANGO_SYNC_TOKEN': ''}):
            response = self.client.post(
                reverse('sync:panel'),
                {
                    'action': 'save_connection',
                    'remote_url': 'https://tienda-demo.onrender.com',
                    'sync_token': '',
                },
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ingrese el token de sincronizacion')

    def test_panel_toggle_pauses_and_resumes_sync_from_store_ui(self):
        response = self.client.post(
            reverse('sync:panel'),
            {'action': 'toggle_sync', 'enabled': '0'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sync Pausado')
        self.assertContains(response, 'Activar sincronizacion')

        response = self.client.post(
            reverse('sync:panel'),
            {'action': 'toggle_sync', 'enabled': '1'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sync Activo')
        self.assertContains(response, 'Desactivar sincronizacion')

    def test_panel_sync_now_stops_when_sync_is_paused(self):
        set_remote_sync_enabled(False, self.user)

        response = self.client.post(
            reverse('sync:panel'),
            {'action': 'sync_now'},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'La sincronizacion remota esta pausada')

    def test_panel_sync_now_requires_remote_configuration(self):
        with patch.dict(os.environ, {
            'SYNC_NODE_ROLE': 'local',
            'SYNC_REMOTE_URL': '',
            'SYNC_API_TOKEN': '',
            'DJANGO_SYNC_TOKEN': '',
        }):
            response = self.client.post(
                reverse('sync:panel'),
                {'action': 'sync_now'},
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Configure SYNC_REMOTE_URL y SYNC_API_TOKEN')

    def test_panel_sync_now_uses_connection_saved_from_store_ui(self):
        update_sync_connection('https://tienda-demo.onrender.com', 'secret-token', self.user)

        with patch.dict(os.environ, {
            'SYNC_NODE_ROLE': 'local',
            'SYNC_REMOTE_URL': '',
            'SYNC_API_TOKEN': '',
            'DJANGO_SYNC_TOKEN': '',
        }), patch('app.core.sync.views.call_command') as mocked_call_command:
            response = self.client.post(
                reverse('sync:panel'),
                {'action': 'sync_now'},
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        mocked_call_command.assert_called_once_with(
            'sync_with_remote',
            remote='https://tienda-demo.onrender.com',
            token='secret-token',
            verbosity=0,
        )

    def test_sync_status_reports_direction_metadata(self):
        with patch.dict(os.environ, {'SYNC_NODE_ROLE': 'central', 'SYNC_API_TOKEN': 'secret'}):
            response = self.client.get(reverse('sync:status'), HTTP_X_SYNC_TOKEN='secret')

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload['node_role'], 'central')
        self.assertTrue(payload['sync_enabled'])
        self.assertIn('erp.product', payload['outgoing_models'])
        self.assertIn('erp.sale', payload['incoming_models'])

    def test_sync_status_reports_when_sync_is_paused(self):
        set_remote_sync_enabled(False, self.user)

        with patch.dict(os.environ, {'SYNC_NODE_ROLE': 'central', 'SYNC_API_TOKEN': 'secret'}):
            response = self.client.get(reverse('sync:status'), HTTP_X_SYNC_TOKEN='secret')

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(payload['sync_enabled'])
