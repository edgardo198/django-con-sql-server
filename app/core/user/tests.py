import io

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client as DjangoClient, RequestFactory, TestCase
from django.urls import reverse

from app.core.user.access import (
    ROLE_SELLER,
    ROLE_STORE_ADMIN,
    ROLE_SUBMANAGER,
    ROLE_SUPER_ADMIN,
    ensure_role_groups,
)
from app.core.user.forms import UserForm
from app.core.user.models import Organization
from app.core.user.views import UserListView


class UserAccessAndBootstrapTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.groups = ensure_role_groups()
        self.user_model = get_user_model()

        self.organization = Organization.objects.create(name='Centro', code='CENTRO')
        self.other_organization = Organization.objects.create(name='Norte', code='NORTE')

        self.super_admin = self.user_model.objects.create_superuser(
            username='root',
            email='root@example.com',
            password='StrongPass123!',
        )
        self.super_admin.organizations.add(self.organization, self.other_organization)
        self.super_admin.current_organization = self.organization
        self.super_admin.save(update_fields=['current_organization'])
        self.super_admin.groups.add(self.groups[ROLE_SUPER_ADMIN])

        self.store_admin = self.user_model.objects.create_user(
            username='storeadmin',
            email='storeadmin@example.com',
            password='StrongPass123!',
        )
        self.store_admin.organizations.add(self.organization)
        self.store_admin.current_organization = self.organization
        self.store_admin.save(update_fields=['current_organization'])
        self.store_admin.groups.add(self.groups[ROLE_STORE_ADMIN])

        self.same_store_seller = self.user_model.objects.create_user(
            username='seller1',
            email='seller1@example.com',
            password='StrongPass123!',
        )
        self.same_store_seller.organizations.add(self.organization)
        self.same_store_seller.current_organization = self.organization
        self.same_store_seller.save(update_fields=['current_organization'])
        self.same_store_seller.groups.add(self.groups[ROLE_SELLER])

        self.other_store_user = self.user_model.objects.create_user(
            username='subnorte',
            email='subnorte@example.com',
            password='StrongPass123!',
        )
        self.other_store_user.organizations.add(self.other_organization)
        self.other_store_user.current_organization = self.other_organization
        self.other_store_user.save(update_fields=['current_organization'])
        self.other_store_user.groups.add(self.groups[ROLE_SUBMANAGER])

    def test_role_groups_are_created_with_expected_permissions(self):
        self.assertIn(ROLE_SUPER_ADMIN, self.groups)
        self.assertIn(ROLE_STORE_ADMIN, self.groups)
        self.assertIn(ROLE_SUBMANAGER, self.groups)
        self.assertIn(ROLE_SELLER, self.groups)

        store_admin_permissions = set(self.groups[ROLE_STORE_ADMIN].permissions.values_list('codename', flat=True))
        seller_permissions = set(self.groups[ROLE_SELLER].permissions.values_list('codename', flat=True))

        self.assertIn('change_user', store_admin_permissions)
        self.assertIn('view_organization', store_admin_permissions)
        self.assertIn('view_supplier', store_admin_permissions)
        self.assertIn('add_purchase', store_admin_permissions)
        self.assertIn('change_cashsession', store_admin_permissions)
        self.assertIn('view_inventorymovement', store_admin_permissions)
        self.assertIn('add_sale', seller_permissions)
        self.assertIn('view_cashsession', seller_permissions)
        self.assertIn('add_salepayment', seller_permissions)
        self.assertNotIn('change_user', seller_permissions)
        self.assertNotIn('add_purchase', seller_permissions)

    def test_store_admin_form_is_limited_to_lower_roles_and_owned_stores(self):
        request = self.factory.get('/user/add/')
        request.user = self.store_admin

        form = UserForm(request=request)

        self.assertCountEqual(
            list(form.fields['groups'].queryset.values_list('name', flat=True)),
            [ROLE_SELLER, ROLE_SUBMANAGER],
        )
        self.assertEqual(
            list(form.fields['organizations'].queryset.values_list('name', flat=True)),
            [self.organization.name],
        )

    def test_store_admin_user_queryset_excludes_superadmins_and_other_stores(self):
        request = self.factory.get('/user/list/')
        request.user = self.store_admin

        view = UserListView()
        view.request = request

        usernames = list(view.get_queryset().values_list('username', flat=True))

        self.assertIn(self.store_admin.username, usernames)
        self.assertIn(self.same_store_seller.username, usernames)
        self.assertNotIn(self.super_admin.username, usernames)
        self.assertNotIn(self.other_store_user.username, usernames)

    def test_store_admin_user_queryset_excludes_same_level_admins(self):
        peer_store_admin = self.user_model.objects.create_user(
            username='storeadmin2',
            email='storeadmin2@example.com',
            password='StrongPass123!',
        )
        peer_store_admin.organizations.add(self.organization)
        peer_store_admin.current_organization = self.organization
        peer_store_admin.save(update_fields=['current_organization'])
        peer_store_admin.groups.add(self.groups[ROLE_STORE_ADMIN])

        request = self.factory.get('/user/list/')
        request.user = self.store_admin

        view = UserListView()
        view.request = request

        usernames = list(view.get_queryset().values_list('username', flat=True))

        self.assertNotIn(peer_store_admin.username, usernames)

    def test_organization_list_ajax_supports_datatables_payload(self):
        self.client.force_login(self.super_admin)

        simple_response = self.client.post(
            reverse('user:organization_list'),
            {'action': 'searchdata'},
        )
        datatable_response = self.client.post(
            reverse('user:organization_list'),
            {'action': 'searchdata', 'draw': '3', 'start': '0', 'length': '10'},
        )

        self.assertEqual(simple_response.status_code, 200)
        self.assertIsInstance(simple_response.json(), list)
        payload = datatable_response.json()
        self.assertEqual(datatable_response.status_code, 200)
        self.assertEqual(payload['draw'], 3)
        self.assertEqual(payload['recordsTotal'], 2)
        self.assertEqual(len(payload['data']), 2)
        self.assertEqual(payload['data'][0]['name'], 'Centro')

    def test_user_list_ajax_supports_datatables_payload(self):
        self.client.force_login(self.store_admin)

        simple_response = self.client.post(
            reverse('user:user_list'),
            {'action': 'searchdata'},
        )
        datatable_response = self.client.post(
            reverse('user:user_list'),
            {'action': 'searchdata', 'draw': '4', 'start': '0', 'length': '10'},
        )

        self.assertEqual(simple_response.status_code, 200)
        simple_usernames = [item['username'] for item in simple_response.json()]
        self.assertIn(self.store_admin.username, simple_usernames)
        self.assertIn(self.same_store_seller.username, simple_usernames)
        self.assertNotIn(self.super_admin.username, simple_usernames)

        payload = datatable_response.json()
        self.assertEqual(datatable_response.status_code, 200)
        self.assertEqual(payload['draw'], 4)
        self.assertEqual(payload['recordsTotal'], 2)
        self.assertEqual(len(payload['data']), 2)

    def test_user_and_organization_datatables_work_with_csrf_enabled(self):
        client = DjangoClient(enforce_csrf_checks=True)
        client.force_login(self.super_admin)

        organization_page = client.get(reverse('user:organization_list'))
        csrf_token = client.cookies['csrftoken'].value
        organization_response = client.post(
            reverse('user:organization_list'),
            {'action': 'searchdata', 'draw': '1', 'start': '0', 'length': '10'},
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        user_page = client.get(reverse('user:user_list'))
        csrf_token = client.cookies['csrftoken'].value
        user_response = client.post(
            reverse('user:user_list'),
            {'action': 'searchdata', 'draw': '2', 'start': '0', 'length': '10'},
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(organization_page.status_code, 200)
        self.assertEqual(organization_response.status_code, 200)
        self.assertEqual(organization_response.json()['draw'], 1)
        self.assertEqual(user_page.status_code, 200)
        self.assertEqual(user_response.status_code, 200)
        self.assertEqual(user_response.json()['draw'], 2)

    def test_bootstrap_access_command_creates_super_admin_and_group_membership(self):
        stdout = io.StringIO()
        call_command(
            'bootstrap_access',
            username='owner',
            email='owner@example.com',
            password='OwnerPass123!',
            stdout=stdout,
        )

        user = self.user_model.objects.get(username='owner')

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.groups.filter(name=ROLE_SUPER_ADMIN).exists())
