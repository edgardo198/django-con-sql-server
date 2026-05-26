import json
import os
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from app.core.backup.services import BACKUP_PREFIX, create_local_backup, list_local_backups


class LocalBackupInterfaceTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.backup_dir = Path(self.temp_dir.name)
        self.env_patch = patch.dict(os.environ, {'LOCAL_BACKUP_DIR': str(self.backup_dir)})
        self.env_patch.start()

        self.user = get_user_model().objects.create_user(username='backup_user', password='secret123')
        self.admin = get_user_model().objects.create_superuser(username='backup_admin', password='secret123')

    def tearDown(self):
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def make_backup_zip(self, filename=None):
        filename = filename or '{}-20260525-120000-test.zip'.format(BACKUP_PREFIX)
        path = self.backup_dir / filename
        manifest = {
            'format': 'erp-local-backup-v1',
            'created_at': timezone.now().isoformat(),
            'django_version': '4.1.13',
            'database': {'name': 'test-db'},
            'contains': {'data_json': True, 'media': False},
        }
        with zipfile.ZipFile(path, 'w') as zip_file:
            zip_file.writestr('data.json', '[]')
            zip_file.writestr('manifest.json', json.dumps(manifest))
        return path

    def test_backup_page_requires_superuser(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('backup:local'))

        self.assertEqual(response.status_code, 403)

    def test_backup_page_lists_existing_backups(self):
        backup_path = self.make_backup_zip()
        self.client.force_login(self.admin)

        response = self.client.get(reverse('backup:local'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, backup_path.name)
        self.assertContains(response, 'Respaldos locales')

    @override_settings(MEDIA_ROOT='')
    def test_backup_page_can_create_backup(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('backup:local'),
            {
                'action': 'create',
                'label': 'cierre dia',
                'keep': '14',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        backups = list_local_backups()
        self.assertEqual(len(backups), 1)
        self.assertIn('cierre-dia', backups[0]['filename'])
        self.assertContains(response, 'Respaldo creado')

    def test_backup_download_returns_zip_file(self):
        backup_path = self.make_backup_zip()
        self.client.force_login(self.admin)

        response = self.client.get(reverse('backup:download', args=[backup_path.name]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/zip')
        self.assertIn('attachment', response['Content-Disposition'])

    def test_backup_download_rejects_path_traversal(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('backup:download', args=['../secret.zip']))

        self.assertEqual(response.status_code, 404)

    def test_backup_page_can_delete_backup(self):
        backup_path = self.make_backup_zip()
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('backup:local'),
            {
                'action': 'delete',
                'filename': backup_path.name,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(backup_path.exists())
        self.assertContains(response, 'Respaldo eliminado')

    def test_restore_requires_confirmation_text(self):
        backup_path = self.make_backup_zip()
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('backup:local'),
            {
                'action': 'restore',
                'filename': backup_path.name,
                'confirmation': 'NO',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Escribe RESTAURAR')
        self.assertTrue(backup_path.exists())

    @override_settings(MEDIA_ROOT='')
    def test_create_local_backup_service_writes_manifest(self):
        result = create_local_backup(output_dir=self.backup_dir, label='manual', include_media=False)

        self.assertTrue(result['path'].exists())
        with zipfile.ZipFile(result['path'], 'r') as zip_file:
            self.assertIn('data.json', zip_file.namelist())
            self.assertIn('manifest.json', zip_file.namelist())
