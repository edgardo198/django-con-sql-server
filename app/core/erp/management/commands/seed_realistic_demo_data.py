from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from app.core.erp.models import (
    CashMovement,
    CashSession,
    Category,
    Client,
    DetPurchase,
    DetSale,
    FiscalData,
    Product,
    Purchase,
    Sale,
    Supplier,
    TaxRate,
    money,
)
from app.core.user.access import ROLE_SELLER, ROLE_STORE_ADMIN, ensure_role_groups
from app.core.user.models import Organization


def dec(value):
    return Decimal(str(value))


DEMO_PASSWORD = 'Demo12345!'


COMPANIES = [
    {
        'name': 'Ferreteria El Roble',
        'code': 'FER-ROB',
        'rtn': '08011999010001',
        'phone': '2234-1001',
        'email': 'ventas@ferreteriaelroble.test',
        'address': 'Barrio El Centro, Tegucigalpa',
        'business_name': 'Inversiones El Roble S. de R.L.',
        'trade_name': 'Ferreteria El Roble',
        'invoice_prefix': '001-001-01-',
        'categories': [
            ('Herramientas manuales', 'Martillos, llaves, cintas metricas y equipo manual'),
            ('Electricidad', 'Material electrico residencial y comercial'),
            ('Pinturas y acabados', 'Pinturas, brochas, selladores y acabados'),
        ],
        'taxes': [('ISV 15', 'ISV15', '15.00', True), ('Exento', 'EXE', '0.00', False)],
        'suppliers': [
            ('Distribuidora Industrial Honduras', '08011999020001', 'Carlos Mejia', '2234-2001', 'ventas@dih.test', 'Anillo periferico, Tegucigalpa'),
            ('Pinturas del Valle', '08011999020002', 'Sofia Rivera', '2234-2002', 'pedidos@pinturasvalle.test', 'Zona industrial, Comayaguela'),
        ],
        'clients': [
            ('Mario', 'Castillo', '0801198501001', '08011999030001', '9488-1001', 'mario.castillo@example.test', 'Colonia Kennedy'),
            ('Constructora', 'Avila', '0801198501002', '08011999030002', '9488-1002', 'compras@avila.test', 'Boulevard Morazan'),
        ],
        'products': [
            ('Martillo de una pieza 16 oz', 'Herramientas manuales', 'FER-0001', 'HR-MAR-16', 'Martillo de acero con mango antideslizante', 'unidad', '115.00', '185.00', 28, 6, 'ISV15'),
            ('Taladro percutor 1/2 pulgada', 'Herramientas manuales', 'FER-0002', 'EL-TAL-12', 'Taladro percutor para concreto y metal', 'unidad', '1180.00', '1695.00', 8, 2, 'ISV15'),
            ('Cable electrico THHN #12', 'Electricidad', 'FER-0003', 'EL-CAB-12', 'Rollo de cable electrico calibre 12', 'metro', '14.00', '24.00', 180, 40, 'ISV15'),
            ('Pintura acrilica blanca galon', 'Pinturas y acabados', 'FER-0004', 'PI-BLA-GAL', 'Pintura blanca lavable para interiores', 'unidad', '310.00', '455.00', 35, 8, 'ISV15'),
        ],
        'purchase': {'supplier': 'Distribuidora Industrial Honduras', 'number': 'FER-COMP-001', 'invoice': 'DIH-84321', 'items': [('FER-0001', 12, '108.00'), ('FER-0002', 3, '1120.00')]},
        'sale': {'client_dni': '0801198501001', 'number': 'FER-VTA-001', 'items': [('FER-0001', 2, '185.00'), ('FER-0003', 15, '24.00')]},
    },
    {
        'name': 'Farmacia Santa Lucia',
        'code': 'FAR-SLU',
        'rtn': '08011999010002',
        'phone': '2234-1101',
        'email': 'contacto@farmaciasantalucia.test',
        'address': 'Avenida La Paz, Tegucigalpa',
        'business_name': 'Farmacia Santa Lucia S.A.',
        'trade_name': 'Farmacia Santa Lucia',
        'invoice_prefix': '002-001-01-',
        'categories': [
            ('Medicamentos OTC', 'Medicamentos de venta libre'),
            ('Cuidado personal', 'Higiene, desinfeccion y cuidado diario'),
            ('Bebes', 'Productos para bebes y maternidad'),
        ],
        'taxes': [('ISV 15', 'ISV15', '15.00', True), ('Exento salud', 'SAL0', '0.00', False)],
        'suppliers': [
            ('Laboratorios Centroamericanos', '08011999021001', 'Diana Santos', '2234-2101', 'pedidos@labca.test', 'San Pedro Sula'),
            ('Distribuidora Medica Maya', '08011999021002', 'Victor Flores', '2234-2102', 'ventas@medicamaya.test', 'Comayagua'),
        ],
        'clients': [
            ('Andrea', 'Lopez', '0801199002001', '08011999031001', '9488-2001', 'andrea.lopez@example.test', 'Residencial Las Uvas'),
            ('Clinica', 'Esperanza', '0801199002002', '08011999031002', '9488-2002', 'compras@clinicaesperanza.test', 'Colonia Palmira'),
        ],
        'products': [
            ('Paracetamol 500mg caja 100 tabletas', 'Medicamentos OTC', 'FAR-0001', 'MED-PAR-500', 'Analgesico y antipiretico', 'caja', '82.00', '128.00', 60, 12, 'SAL0'),
            ('Alcohol gel 70% 500ml', 'Cuidado personal', 'FAR-0002', 'CP-ALG-500', 'Gel antibacterial de uso frecuente', 'unidad', '48.00', '82.00', 45, 10, 'ISV15'),
            ('Panal etapa 3 paquete 40 unidades', 'Bebes', 'FAR-0003', 'BB-PAN-03', 'Panal desechable etapa 3', 'paquete', '275.00', '395.00', 22, 5, 'ISV15'),
            ('Termometro digital flexible', 'Cuidado personal', 'FAR-0004', 'CP-TER-DIG', 'Termometro digital de lectura rapida', 'unidad', '95.00', '165.00', 18, 4, 'ISV15'),
        ],
        'purchase': {'supplier': 'Laboratorios Centroamericanos', 'number': 'FAR-COMP-001', 'invoice': 'LAB-55312', 'items': [('FAR-0001', 20, '78.00'), ('FAR-0002', 12, '45.00')]},
        'sale': {'client_dni': '0801199002001', 'number': 'FAR-VTA-001', 'items': [('FAR-0001', 2, '128.00'), ('FAR-0004', 1, '165.00')]},
    },
    {
        'name': 'Mini Super La Esquina',
        'code': 'SUP-ESQ',
        'rtn': '08011999010003',
        'phone': '2234-1201',
        'email': 'admin@minisuperlaesquina.test',
        'address': 'Colonia Miraflores, Tegucigalpa',
        'business_name': 'Comercial La Esquina S.A.',
        'trade_name': 'Mini Super La Esquina',
        'invoice_prefix': '003-001-01-',
        'categories': [
            ('Abarrotes', 'Granos, aceites, cafe y productos basicos'),
            ('Bebidas', 'Refrescos, jugos y agua embotellada'),
            ('Limpieza', 'Productos para limpieza del hogar'),
        ],
        'taxes': [('ISV 15', 'ISV15', '15.00', True), ('Exento canasta basica', 'BAS0', '0.00', False)],
        'suppliers': [
            ('Mayorista La Despensa', '08011999022001', 'Ruth Hernandez', '2234-2201', 'ventas@despensa.test', 'Mercado Zonal Belen'),
            ('Bebidas Atlantida', '08011999022002', 'Jorge Reyes', '2234-2202', 'pedidos@bebidasatlantida.test', 'La Ceiba'),
        ],
        'clients': [
            ('Claudia', 'Mendoza', '0801198803001', '08011999032001', '9488-3001', 'claudia.mendoza@example.test', 'Colonia Miraflores'),
            ('Pulperia', 'San Miguel', '0801198803002', '08011999032002', '9488-3002', 'pulperiasanmiguel@example.test', 'Aldea El Hatillo'),
        ],
        'products': [
            ('Arroz precocido bolsa 5 lb', 'Abarrotes', 'SUP-0001', 'ABA-ARR-5LB', 'Arroz blanco precocido', 'libra', '72.00', '98.00', 80, 15, 'BAS0'),
            ('Aceite vegetal 1 litro', 'Abarrotes', 'SUP-0002', 'ABA-ACE-1L', 'Aceite vegetal para cocina', 'litro', '58.00', '79.00', 75, 18, 'BAS0'),
            ('Cafe molido premium 400g', 'Abarrotes', 'SUP-0003', 'ABA-CAF-400', 'Cafe hondureno molido', 'unidad', '88.00', '125.00', 50, 10, 'ISV15'),
            ('Detergente multiuso 900g', 'Limpieza', 'SUP-0004', 'LIM-DET-900', 'Detergente en polvo multiuso', 'unidad', '54.00', '82.00', 38, 8, 'ISV15'),
        ],
        'purchase': {'supplier': 'Mayorista La Despensa', 'number': 'SUP-COMP-001', 'invoice': 'DSP-90210', 'items': [('SUP-0001', 20, '68.00'), ('SUP-0002', 18, '54.00')]},
        'sale': {'client_dni': '0801198803001', 'number': 'SUP-VTA-001', 'items': [('SUP-0001', 3, '98.00'), ('SUP-0003', 2, '125.00'), ('SUP-0004', 1, '82.00')]},
    },
    {
        'name': 'Restaurante La Ceiba Grill',
        'code': 'RES-LCG',
        'rtn': '08011999010004',
        'phone': '2234-1301',
        'email': 'reservas@laceibagrill.test',
        'address': 'Boulevard Suyapa, Tegucigalpa',
        'business_name': 'Gastronomia Atlantica S. de R.L.',
        'trade_name': 'Restaurante La Ceiba Grill',
        'invoice_prefix': '004-001-01-',
        'categories': [
            ('Platos preparados', 'Platos principales listos para venta'),
            ('Bebidas naturales', 'Jugos, cafe y bebidas sin alcohol'),
            ('Postres', 'Postres de la casa'),
        ],
        'taxes': [('ISV 15', 'ISV15', '15.00', True)],
        'suppliers': [
            ('Carnes Premium del Norte', '08011999023001', 'Hector Molina', '2234-2301', 'ventas@carnespremium.test', 'San Pedro Sula'),
            ('Verduras Frescas Zamorano', '08011999023002', 'Paola Diaz', '2234-2302', 'pedidos@verduraszamorano.test', 'Valle de Yeguare'),
        ],
        'clients': [
            ('Roberto', 'Alvarado', '0801198704001', '08011999033001', '9488-4001', 'roberto.alvarado@example.test', 'Colonia El Trapiche'),
            ('Eventos', 'Capital', '0801198704002', '08011999033002', '9488-4002', 'reservas@eventoscapital.test', 'Torre Morazan'),
        ],
        'products': [
            ('Almuerzo ejecutivo pollo', 'Platos preparados', 'RES-0001', 'PL-ALM-POL', 'Plato preparado con pollo, arroz y ensalada', 'unidad', '72.00', '125.00', 0, 0, 'ISV15'),
            ('Parrillada mixta personal', 'Platos preparados', 'RES-0002', 'PL-PAR-MIX', 'Parrillada personal con guarniciones', 'unidad', '145.00', '245.00', 0, 0, 'ISV15'),
            ('Jugo natural de maracuya', 'Bebidas naturales', 'RES-0003', 'BE-JUG-MAR', 'Jugo natural preparado al momento', 'unidad', '18.00', '42.00', 0, 0, 'ISV15'),
            ('Tres leches de la casa', 'Postres', 'RES-0004', 'PO-TLE-CAS', 'Postre tres leches por porcion', 'unidad', '35.00', '68.00', 0, 0, 'ISV15'),
        ],
        'services': ['RES-0001', 'RES-0002', 'RES-0003', 'RES-0004'],
        'purchase': {'supplier': 'Carnes Premium del Norte', 'number': 'RES-COMP-001', 'invoice': 'CAR-12098', 'items': [('RES-0002', 5, '138.00')]},
        'sale': {'client_dni': '0801198704001', 'number': 'RES-VTA-001', 'items': [('RES-0001', 2, '125.00'), ('RES-0003', 2, '42.00'), ('RES-0004', 1, '68.00')]},
    },
    {
        'name': 'Distribuidora AgroNorte',
        'code': 'AGR-NOR',
        'rtn': '08011999010005',
        'phone': '2234-1401',
        'email': 'ventas@agronorte.test',
        'address': 'Salida a Olancho, Tegucigalpa',
        'business_name': 'Agroservicios del Norte S.A.',
        'trade_name': 'Distribuidora AgroNorte',
        'invoice_prefix': '005-001-01-',
        'categories': [
            ('Fertilizantes', 'Fertilizantes y enmiendas de suelo'),
            ('Semillas', 'Semillas certificadas para siembra'),
            ('Proteccion agricola', 'Herbicidas, fungicidas e insecticidas'),
        ],
        'taxes': [('ISV 15', 'ISV15', '15.00', True), ('Exento agricola', 'AGR0', '0.00', False)],
        'suppliers': [
            ('Agroquimicos del Istmo', '08011999024001', 'Manuel Zelaya', '2234-2401', 'ventas@agroistmo.test', 'Choluteca'),
            ('Semillas Tropicales', '08011999024002', 'Laura Matamoros', '2234-2402', 'pedidos@semillastropicales.test', 'Juticalpa'),
        ],
        'clients': [
            ('Cooperativa', 'El Maizal', '0801198605001', '08011999034001', '9488-5001', 'compras@elmaizal.test', 'Guayape, Olancho'),
            ('Finca', 'Los Pinos', '0801198605002', '08011999034002', '9488-5002', 'admin@lospinos.test', 'Talanga'),
        ],
        'products': [
            ('Fertilizante 18-46-0 saco 100 lb', 'Fertilizantes', 'AGR-0001', 'FER-1846-100', 'Fertilizante fosfatado granulado', 'libra', '920.00', '1280.00', 30, 6, 'AGR0'),
            ('Semilla maiz hibrido bolsa 60k', 'Semillas', 'AGR-0002', 'SEM-MAI-60K', 'Semilla certificada de maiz hibrido', 'unidad', '1480.00', '1980.00', 15, 3, 'AGR0'),
            ('Herbicida sistemico 1 litro', 'Proteccion agricola', 'AGR-0003', 'PRO-HER-1L', 'Herbicida sistemico concentrado', 'litro', '285.00', '410.00', 25, 5, 'ISV15'),
            ('Fungicida preventivo 500g', 'Proteccion agricola', 'AGR-0004', 'PRO-FUN-500', 'Fungicida preventivo para cultivos', 'unidad', '190.00', '285.00', 18, 4, 'ISV15'),
        ],
        'purchase': {'supplier': 'Agroquimicos del Istmo', 'number': 'AGR-COMP-001', 'invoice': 'AGI-33440', 'items': [('AGR-0001', 8, '900.00'), ('AGR-0003', 6, '275.00')]},
        'sale': {'client_dni': '0801198605001', 'number': 'AGR-VTA-001', 'items': [('AGR-0001', 2, '1280.00'), ('AGR-0003', 1, '410.00')]},
    },
]


class Command(BaseCommand):
    help = 'Crea varias empresas demo con datos realistas para pruebas funcionales.'

    def add_arguments(self, parser):
        parser.add_argument('--password', default=DEMO_PASSWORD)
        parser.add_argument(
            '--attach-users',
            default='Tato,qa_tester',
            help='Usuarios existentes a los que se les dara acceso a las empresas demo.',
        )

    def handle(self, *args, **options):
        groups = ensure_role_groups()
        password = options['password']
        user_model = get_user_model()

        admin_user, _ = user_model.objects.get_or_create(
            username='demo_admin',
            defaults={
                'first_name': 'Admin',
                'last_name': 'Demo',
                'email': 'demo_admin@example.test',
                'is_active': True,
            },
        )
        admin_user.set_password(password)
        admin_user.is_active = True
        admin_user.email = 'demo_admin@example.test'
        admin_user.save()
        admin_user.groups.set([groups[ROLE_STORE_ADMIN]])

        seller_user, _ = user_model.objects.get_or_create(
            username='demo_vendedor',
            defaults={
                'first_name': 'Vendedor',
                'last_name': 'Demo',
                'email': 'demo_vendedor@example.test',
                'is_active': True,
            },
        )
        seller_user.set_password(password)
        seller_user.is_active = True
        seller_user.email = 'demo_vendedor@example.test'
        seller_user.save()
        seller_user.groups.set([groups[ROLE_SELLER]])

        attach_usernames = [
            username.strip()
            for username in options['attach_users'].split(',')
            if username.strip()
        ]
        attach_users = list(user_model.objects.filter(username__in=attach_usernames))

        created_orgs = []
        stats = {'organizations': 0, 'products': 0, 'clients': 0, 'suppliers': 0, 'purchases': 0, 'sales': 0}

        with transaction.atomic():
            for company in COMPANIES:
                organization = self.seed_company(company, admin_user, stats)
                created_orgs.append(organization)

            for organization in created_orgs:
                admin_user.organizations.add(organization)
                seller_user.organizations.add(organization)
                for user in attach_users:
                    user.organizations.add(organization)
                    if not user.current_organization_id:
                        user.current_organization = organization
                        user.save(update_fields=['current_organization'])

            if created_orgs:
                admin_user.current_organization = created_orgs[0]
                admin_user.save(update_fields=['current_organization'])
                seller_user.current_organization = created_orgs[0]
                seller_user.save(update_fields=['current_organization'])

        self.stdout.write(self.style.SUCCESS('Datos demo realistas creados/actualizados correctamente.'))
        self.stdout.write(f'Empresas disponibles: {", ".join(org.name for org in created_orgs)}')
        self.stdout.write(f'Usuario admin demo: demo_admin / {password}')
        self.stdout.write(f'Usuario vendedor demo: demo_vendedor / {password}')
        self.stdout.write(
            'Resumen: {organizations} empresas, {products} productos, {clients} clientes, '
            '{suppliers} proveedores, {purchases} compras, {sales} ventas.'.format(**stats)
        )

    def seed_company(self, company, admin_user, stats):
        organization, created = Organization.objects.update_or_create(
            name=company['name'],
            defaults={
                'code': company['code'],
                'rtn': company['rtn'],
                'phone': company['phone'],
                'email': company['email'],
                'address': company['address'],
                'is_active': True,
            },
        )
        if created:
            stats['organizations'] += 1

        tax_rates = {}
        for tax_name, code, rate, is_default in company['taxes']:
            tax, _ = TaxRate.objects.update_or_create(
                organization=organization,
                code=code,
                defaults={'name': tax_name, 'rate': dec(rate), 'is_default': is_default, 'is_active': True},
            )
            tax_rates[code] = tax
        default_tax = next((tax for tax in tax_rates.values() if tax.is_default), None)
        if default_tax:
            TaxRate.objects.filter(organization=organization).exclude(pk=default_tax.pk).update(is_default=False)

        categories = {}
        for name, description in company['categories']:
            category, _ = Category.objects.update_or_create(
                organization=organization,
                name=name,
                defaults={'description': description, 'desc': description, 'is_active': True},
            )
            categories[name] = category

        suppliers = {}
        for name, rtn, contact, phone, email, address in company['suppliers']:
            supplier, supplier_created = Supplier.objects.update_or_create(
                organization=organization,
                name=name,
                defaults={
                    'rtn': rtn,
                    'contact_name': contact,
                    'phone': phone,
                    'email': email,
                    'address': address,
                    'is_active': True,
                },
            )
            suppliers[name] = supplier
            if supplier_created:
                stats['suppliers'] += 1

        clients = {}
        for names, surnames, dni, rtn, phone, email, address in company['clients']:
            client, client_created = Client.objects.update_or_create(
                organization=organization,
                dni=dni,
                defaults={
                    'names': names,
                    'surnames': surnames,
                    'rtn': rtn,
                    'phone': phone,
                    'email': email,
                    'address': address,
                    'gender': 'other',
                    'credit_limit': dec('2500.00'),
                    'is_credit_customer': True,
                    'is_active': True,
                },
            )
            clients[dni] = client
            if client_created:
                stats['clients'] += 1

        products = {}
        service_codes = set(company.get('services', []))
        for name, category_name, barcode, internal_code, description, unit, cost, pvp, stock, min_stock, tax_code in company['products']:
            product, product_created = Product.objects.get_or_create(
                organization=organization,
                barcode=barcode,
                defaults={
                    'name': name,
                    'category': categories[category_name],
                    'cat': categories[category_name],
                    'internal_code': internal_code,
                    'description': description,
                    'unit': unit,
                    'cost': dec(cost),
                    'pvp': dec(pvp),
                    'stock': stock,
                    'min_stock': min_stock,
                    'tax_rate': tax_rates[tax_code],
                    'allow_decimal_qty': unit in ('metro', 'libra', 'litro'),
                    'is_service': barcode in service_codes,
                    'is_active': True,
                },
            )
            product.name = name
            product.category = categories[category_name]
            product.cat = categories[category_name]
            product.internal_code = internal_code
            product.description = description
            product.unit = unit
            product.cost = dec(cost)
            product.pvp = dec(pvp)
            product.min_stock = min_stock
            product.tax_rate = tax_rates[tax_code]
            product.allow_decimal_qty = unit in ('metro', 'libra', 'litro')
            product.is_service = barcode in service_codes
            product.is_active = True
            product.save()
            products[barcode] = product
            if product_created:
                stats['products'] += 1

        self.seed_fiscal_data(organization, company)
        cash_session = self.seed_cash_session(organization, admin_user)
        self.seed_purchase(organization, company['purchase'], suppliers, products, admin_user, stats)
        self.seed_sale(organization, company['sale'], clients, products, cash_session, admin_user, stats)
        return organization

    def seed_fiscal_data(self, organization, company):
        fiscal, created = FiscalData.objects.get_or_create(
            organization=organization,
            defaults={
                'business_name': company['business_name'],
                'trade_name': company['trade_name'],
                'rtn': company['rtn'],
                'address': company['address'],
                'phone': company['phone'],
                'email': company['email'],
                'cai': f"CAI-{company['code']}-2026",
                'cai_start_date': timezone.localdate(),
                'cai_end_date': timezone.localdate() + timedelta(days=365),
                'invoice_prefix': company['invoice_prefix'],
                'invoice_range_start': 1,
                'invoice_range_end': 99999999,
                'next_invoice_number': 1,
                'cash_sale_legend': 'La factura es beneficio de todos. Exijala.',
            },
        )
        fiscal.business_name = company['business_name']
        fiscal.trade_name = company['trade_name']
        fiscal.rtn = company['rtn']
        fiscal.address = company['address']
        fiscal.phone = company['phone']
        fiscal.email = company['email']
        fiscal.cai = f"CAI-{company['code']}-2026"
        fiscal.cai_start_date = timezone.localdate()
        fiscal.cai_end_date = timezone.localdate() + timedelta(days=365)
        fiscal.invoice_prefix = company['invoice_prefix']
        fiscal.invoice_range_start = 1
        fiscal.invoice_range_end = 99999999
        if created:
            fiscal.next_invoice_number = 1
        fiscal.cash_sale_legend = 'La factura es beneficio de todos. Exijala.'
        fiscal.save()

    def seed_cash_session(self, organization, admin_user):
        cash_session, _ = CashSession.objects.get_or_create(
            organization=organization,
            user=admin_user,
            status='open',
            defaults={'opening_amount': dec('1500.00'), 'notes': 'Caja demo abierta'},
        )
        CashMovement.objects.get_or_create(
            organization=organization,
            cash_session=cash_session,
            reference=f'DEMO-{organization.code}-APERTURA',
            defaults={
                'movement_type': 'income',
                'amount': dec('250.00'),
                'description': 'Ingreso inicial de caja demo',
                'user_creation': admin_user,
                'user_updated': admin_user,
            },
        )
        cash_session.recalculate()
        return cash_session

    def seed_purchase(self, organization, purchase_data, suppliers, products, admin_user, stats):
        purchase, created = Purchase.objects.get_or_create(
            organization=organization,
            number=purchase_data['number'],
            defaults={
                'supplier': suppliers[purchase_data['supplier']],
                'supplier_invoice': purchase_data['invoice'],
                'date_joined': timezone.localdate() - timedelta(days=4),
                'payment_term': 'cash',
                'amount_paid': dec('0.00'),
                'observation': 'Compra demo de inventario inicial',
            },
        )
        if not created:
            return purchase

        for barcode, quantity, cost in purchase_data['items']:
            DetPurchase.objects.create(
                purchase=purchase,
                prod=products[barcode],
                cant=quantity,
                cost=dec(cost),
            )
        purchase.refresh_from_db()
        purchase.amount_paid = purchase.total
        purchase.balance = money(purchase.total - purchase.amount_paid)
        purchase.save(update_fields=['amount_paid', 'balance'])
        purchase.confirm(user=admin_user)
        stats['purchases'] += 1
        return purchase

    def seed_sale(self, organization, sale_data, clients, products, cash_session, admin_user, stats):
        sale, created = Sale.objects.get_or_create(
            organization=organization,
            number=sale_data['number'],
            defaults={
                'cli': clients[sale_data['client_dni']],
                'cash_session': cash_session,
                'document_type': 'receipt',
                'payment_term': 'cash',
                'date_joined': timezone.localdate() - timedelta(days=1),
                'amount_paid': dec('0.00'),
                'observation': 'Venta demo confirmada',
            },
        )
        if not created:
            return sale

        for barcode, quantity, price in sale_data['items']:
            product = products[barcode]
            DetSale.objects.create(
                sale=sale,
                prod=product,
                cant=quantity,
                price=dec(price),
                cost=product.cost,
            )
        sale.refresh_from_db()
        sale.amount_paid = sale.total
        sale.balance = money(sale.total - sale.amount_paid)
        sale.save(update_fields=['amount_paid', 'balance'])
        sale.confirm(user=admin_user)
        stats['sales'] += 1
        return sale
