from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from app.core.erp.models import CashSession, Category, Client, FiscalData, Product, Supplier, TaxRate
from app.core.user.access import ROLE_STORE_ADMIN, ensure_role_groups
from app.core.user.models import Organization


class Command(BaseCommand):
    help = 'Crea un perfil QA con tienda y datos base para probar todas las paginas del ERP.'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='qa_tester')
        parser.add_argument('--password', default='QaTest123!')
        parser.add_argument('--email', default='qa_tester@example.com')
        parser.add_argument('--store-name', default='Tienda QA')

    def handle(self, *args, **options):
        groups = ensure_role_groups()
        organization, _ = Organization.objects.update_or_create(
            name=options['store_name'],
            defaults={
                'code': 'QA',
                'rtn': '08011999123456',
                'phone': '2222-3333',
                'email': 'qa-store@example.com',
                'address': 'Direccion de pruebas QA',
                'is_active': True,
            },
        )

        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            username=options['username'],
            defaults={
                'email': options['email'],
                'first_name': 'Usuario',
                'last_name': 'QA',
                'is_active': True,
                'is_staff': False,
            },
        )
        user.email = options['email']
        user.first_name = 'Usuario'
        user.last_name = 'QA'
        user.is_active = True
        user.set_password(options['password'])
        user.save()
        user.organizations.set([organization])
        user.current_organization = organization
        user.groups.set([groups[ROLE_STORE_ADMIN]])
        user.save(update_fields=['current_organization'])

        category, _ = Category.objects.update_or_create(
            organization=organization,
            name='Categoria QA',
            defaults={'description': 'Categoria creada para pruebas', 'desc': 'Categoria creada para pruebas', 'is_active': True},
        )

        tax_rate, _ = TaxRate.objects.update_or_create(
            organization=organization,
            code='QA15',
            defaults={'name': 'ISV QA 15', 'rate': Decimal('15.00'), 'is_default': True, 'is_active': True},
        )
        TaxRate.objects.filter(organization=organization).exclude(pk=tax_rate.pk).update(is_default=False)

        supplier, _ = Supplier.objects.update_or_create(
            organization=organization,
            name='Proveedor QA',
            defaults={
                'rtn': '08011999123456',
                'contact_name': 'Contacto QA',
                'phone': '2222-4444',
                'email': 'proveedor.qa@example.com',
                'address': 'Bodega QA',
                'is_active': True,
            },
        )

        client, _ = Client.objects.update_or_create(
            organization=organization,
            dni='0801199912345',
            defaults={
                'names': 'Cliente',
                'surnames': 'QA',
                'rtn': '08011999123456',
                'phone': '2222-5555',
                'email': 'cliente.qa@example.com',
                'address': 'Colonia QA',
                'gender': 'other',
                'credit_limit': Decimal('1000.00'),
                'is_credit_customer': True,
                'is_active': True,
            },
        )

        Product.objects.update_or_create(
            organization=organization,
            name='Producto QA',
            defaults={
                'category': category,
                'cat': category,
                'barcode': 'QA-0001',
                'internal_code': 'QA-PROD-001',
                'description': 'Producto para pruebas integrales',
                'unit': 'unidad',
                'cost': Decimal('50.00'),
                'pvp': Decimal('75.00'),
                'stock': 25,
                'min_stock': 5,
                'tax_rate': tax_rate,
                'is_active': True,
            },
        )

        FiscalData.objects.update_or_create(
            organization=organization,
            defaults={
                'business_name': 'Empresa QA S.A.',
                'trade_name': 'Tienda QA',
                'rtn': '08011999123456',
                'address': 'Direccion fiscal QA',
                'phone': '2222-6666',
                'email': 'fiscal.qa@example.com',
                'cai': 'QA-CAI-0001',
                'cai_start_date': timezone.localdate(),
                'cai_end_date': timezone.localdate() + timedelta(days=365),
                'invoice_prefix': '001-001-01-',
                'invoice_range_start': 1,
                'invoice_range_end': 99999999,
                'next_invoice_number': 1,
                'cash_sale_legend': 'Perfil QA para pruebas funcionales',
            },
        )

        CashSession.objects.get_or_create(
            organization=organization,
            user=user,
            status='open',
            defaults={
                'opening_amount': Decimal('100.00'),
                'notes': 'Caja abierta para pruebas QA',
            },
        )

        status = 'creado' if created else 'actualizado'
        self.stdout.write(self.style.SUCCESS(f'Perfil QA {status} correctamente.'))
        self.stdout.write(f'username={user.username}')
        self.stdout.write(f'password={options["password"]}')
        self.stdout.write(f'tienda={organization.name}')
        self.stdout.write(f'proveedor={supplier.name}')
        self.stdout.write(f'cliente={client.get_full_name()}')
