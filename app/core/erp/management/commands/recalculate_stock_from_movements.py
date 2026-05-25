from django.core.management.base import BaseCommand
from django.db import transaction

from app.core.erp.models import Product


class Command(BaseCommand):
    help = 'Recalcula Product.stock usando el ultimo stock_after registrado en movimientos de inventario.'

    def add_arguments(self, parser):
        parser.add_argument('--organization-id', type=int, default=None)
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        queryset = Product.objects.order_by('id')
        if options['organization_id']:
            queryset = queryset.filter(organization_id=options['organization_id'])

        checked = 0
        updated = 0

        with transaction.atomic():
            for product in queryset.select_for_update():
                checked += 1
                latest_movement = product.movements.order_by('-date_joined', '-id').first()
                if not latest_movement:
                    continue

                expected_stock = latest_movement.stock_after
                if product.stock == expected_stock:
                    continue

                updated += 1
                self.stdout.write(
                    '{}: stock {} -> {}'.format(product.name, product.stock, expected_stock)
                )
                if not options['dry_run']:
                    product.stock = expected_stock
                    product._skip_inventory_movement = True
                    Product.save(product, update_fields=['stock', 'date_updated'])

            if options['dry_run']:
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS('Productos revisados: {}. Productos corregidos: {}.'.format(checked, updated))
        )
