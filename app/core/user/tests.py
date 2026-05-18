import io
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
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
from app.core.user.models import Organization, StoredMediaFile
from app.core.user.storage import DatabaseMediaStorage
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

    def test_user_edit_without_password_keeps_current_password(self):
        request = self.factory.post('/user/update/')
        request.user = self.super_admin
        original_password = self.same_store_seller.password
        form = UserForm(
            data={
                'first_name': 'Seller',
                'last_name': 'Updated',
                'email': self.same_store_seller.email,
                'username': self.same_store_seller.username,
                'password': '',
                'groups': [self.groups[ROLE_SELLER].pk],
                'organizations': [self.organization.pk],
                'current_organization': self.organization.pk,
            },
            instance=self.same_store_seller,
            request=request,
        )

        data = form.save()
        self.same_store_seller.refresh_from_db()

        self.assertEqual(data, {})
        self.assertEqual(self.same_store_seller.password, original_password)
        self.assertEqual(self.same_store_seller.last_name, 'Updated')

    def test_user_edit_with_password_updates_password(self):
        request = self.factory.post('/user/update/')
        request.user = self.super_admin
        form = UserForm(
            data={
                'first_name': self.same_store_seller.first_name,
                'last_name': self.same_store_seller.last_name,
                'email': self.same_store_seller.email,
                'username': self.same_store_seller.username,
                'password': 'NewStrongPass123!',
                'groups': [self.groups[ROLE_SELLER].pk],
                'organizations': [self.organization.pk],
                'current_organization': self.organization.pk,
            },
            instance=self.same_store_seller,
            request=request,
        )

        data = form.save()
        self.same_store_seller.refresh_from_db()

        self.assertEqual(data, {})
        self.assertTrue(self.same_store_seller.check_password('NewStrongPass123!'))

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

    def test_user_without_store_reuses_existing_default_store(self):
        user = self.user_model.objects.create_user(
            username='nostore',
            email='nostore@example.com',
            password='StrongPass123!',
        )
        organization = Organization.objects.create(
            name='Tienda Principal nostore',
            code='',
            is_active=False,
        )

        current_organization = user.get_current_organization()
        organization.refresh_from_db()

        self.assertEqual(current_organization, organization)
        self.assertTrue(organization.is_active)
        self.assertEqual(organization.code, 'STORE-{}'.format(user.pk))
        self.assertTrue(user.organizations.filter(pk=organization.pk).exists())
        self.assertEqual(user.current_organization, organization)


class DatabaseMediaStorageTests(TestCase):
    def setUp(self):
        self.storage = DatabaseMediaStorage()
        self.user_model = get_user_model()

    def image_bytes(self):
        image_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'imagen.png')
        with open(image_path, 'rb') as image_file:
            return image_file.read()

    def patch_image_storage(self, *model_fields):
        storage = self.storage

        class StoragePatch:
            def __enter__(self_inner):
                self_inner.originals = []
                for model, field_name in model_fields:
                    field = model._meta.get_field(field_name)
                    self_inner.originals.append((field, field.storage))
                    field.storage = storage
                return storage

            def __exit__(self_inner, exc_type, exc, tb):
                for field, original_storage in self_inner.originals:
                    field.storage = original_storage

        return StoragePatch()

    def test_database_media_storage_serves_exact_and_prefixed_media_paths(self):
        image_data = self.image_bytes()
        saved_name = self.storage.save('product/test-image.jpg', ContentFile(image_data))

        stored_file = StoredMediaFile.objects.get(name=saved_name)
        self.assertEqual(stored_file.size, len(image_data))

        for url in (self.storage.url(saved_name), '/media/media/{}'.format(saved_name)):
            response = self.client.get(url)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, image_data)
            self.assertEqual(response['Content-Type'], 'image/jpeg')
            self.assertEqual(response['Cache-Control'], 'no-store, max-age=0')

    def test_missing_image_media_path_returns_placeholder_instead_of_404(self):
        response = self.client.get('/media/product/missing-image.jpg')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')

    def test_user_and_organization_images_use_database_storage_urls(self):
        image_data = self.image_bytes()

        with self.patch_image_storage((Organization, 'image'), (self.user_model, 'image')):
            organization = Organization.objects.create(name='Media Store', code='MEDIA')
            organization.image.save('logo.jpg', ContentFile(image_data), save=True)

            user = self.user_model.objects.create_user(username='mediauser', password='StrongPass123!')
            user.image.save('avatar.jpg', ContentFile(image_data), save=True)

            organization_image = organization.toJSON()['image']
            user_image = user.toJSON()['image']

        self.assertTrue(organization_image.startswith('/media/organization/'))
        self.assertTrue(user_image.startswith('/media/users/'))
        self.assertTrue(StoredMediaFile.objects.filter(name=organization.image.name).exists())
        self.assertTrue(StoredMediaFile.objects.filter(name=user.image.name).exists())
        self.assertEqual(self.client.get(organization_image).status_code, 200)
        self.assertEqual(self.client.get(user_image).status_code, 200)

    def test_user_and_organization_images_use_placeholders_when_url_fails(self):
        class BrokenStorage:
            def url(self, name):
                raise RuntimeError('storage url failed')

        organization = Organization.objects.create(name='Broken Media Store', code='BROKEN')
        organization.image.name = 'organization/broken-logo.jpg'
        user = self.user_model.objects.create_user(username='brokenmedia', password='StrongPass123!')
        user.image.name = 'users/broken-avatar.jpg'

        organization_field = Organization._meta.get_field('image')
        user_field = self.user_model._meta.get_field('image')
        original_organization_storage = organization_field.storage
        original_user_storage = user_field.storage
        organization_field.storage = BrokenStorage()
        user_field.storage = BrokenStorage()
        try:
            organization = Organization.objects.get(pk=organization.pk)
            organization.image.name = 'organization/broken-logo.jpg'
            user = self.user_model.objects.get(pk=user.pk)
            user.image.name = 'users/broken-avatar.jpg'

            organization_image = organization.get_image()
            user_image = user.get_image()
        finally:
            organization_field.storage = original_organization_storage
            user_field.storage = original_user_storage

        self.assertEqual(organization_image, '{}{}'.format(settings.STATIC_URL, 'img/logo.png'))
        self.assertEqual(user_image, '{}{}'.format(settings.STATIC_URL, 'img/imagen.png'))
