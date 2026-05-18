# Generated manually on 2026-05-18

from django.db import migrations


UNCATEGORIZED_NAME = 'Sin categoria'


def assign_uncategorized_products(apps, schema_editor):
    Category = apps.get_model('erp', 'Category')
    Product = apps.get_model('erp', 'Product')

    organization_ids = (
        Product.objects
        .filter(category__isnull=True, cat__isnull=True)
        .values_list('organization_id', flat=True)
        .distinct()
    )

    for organization_id in organization_ids:
        category = (
            Category.objects
            .filter(organization_id=organization_id, name=UNCATEGORIZED_NAME)
            .order_by('id')
            .first()
        )
        if category is None:
            category = Category.objects.create(
                organization_id=organization_id,
                name=UNCATEGORIZED_NAME,
                description='Productos pendientes de clasificar',
                desc='Productos pendientes de clasificar',
                is_active=True,
            )

        Product.objects.filter(
            organization_id=organization_id,
            category__isnull=True,
            cat__isnull=True,
        ).update(category=category, cat=category)


class Migration(migrations.Migration):

    dependencies = [
        ('erp', '0016_cashmovement_cashsession_fiscaldata_purchasepayment_and_more'),
    ]

    operations = [
        migrations.RunPython(assign_uncategorized_products, migrations.RunPython.noop),
    ]
