import json

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Muestra diagnostico de configuracion y persistencia de archivos media.'

    def handle(self, *args, **options):
        diagnostics = {
            'debug': settings.DEBUG,
            'media_url': settings.MEDIA_URL,
            'media_root': settings.MEDIA_ROOT,
            'serve_media': getattr(settings, 'SERVE_MEDIA', None),
            'use_database_media_storage': getattr(settings, 'USE_DATABASE_MEDIA_STORAGE', None),
            'default_file_storage': getattr(settings, 'DEFAULT_FILE_STORAGE', None),
            'default_storage_class': '{}.{}'.format(
                default_storage.__class__.__module__,
                default_storage.__class__.__name__,
            ),
            'database_engine': settings.DATABASES['default']['ENGINE'],
            'tables': {},
            'stored_media': {},
            'latest_products': [],
        }

        table_names = connection.introspection.table_names()
        stored_media_table = 'user_storedmediafile'
        diagnostics['tables']['stored_media_exists'] = stored_media_table in table_names

        if diagnostics['tables']['stored_media_exists']:
            from app.core.user.models import StoredMediaFile

            latest_files = StoredMediaFile.objects.order_by('-updated_at')[:10]
            diagnostics['stored_media'] = {
                'count': StoredMediaFile.objects.count(),
                'latest': [
                    {
                        'name': item.name,
                        'size': item.size,
                        'content_type': item.content_type,
                    }
                    for item in latest_files
                ],
            }

        if 'erp_product' in table_names:
            from app.core.erp.models import Product

            products = Product.objects.exclude(image='').order_by('-id')[:10]
            diagnostics['latest_products'] = [
                {
                    'id': product.id,
                    'name': product.name,
                    'image': product.image.name,
                    'url': product.image.url if product.image else '',
                    'storage_exists': default_storage.exists(product.image.name) if product.image else False,
                }
                for product in products
            ]

        self.stdout.write(json.dumps(diagnostics, indent=2, ensure_ascii=False))
