from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models, transaction
from django.db.models import Sum
from django.forms import model_to_dict
from django.utils import timezone


# =========================================================
# HELPERS
# =========================================================

TWOPLACES = Decimal("0.01")
DEFAULT_TAX_RATE_PERCENT = Decimal("15.00")


def money(value):
    return Decimal(value or 0).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def calculate_tax(base, rate_percent):
    base = money(base)
    rate_percent = Decimal(rate_percent or 0)
    return money(base * (rate_percent / Decimal("100")))


def effective_tax_rate_percent(tax_rate=None):
    if tax_rate is None:
        return DEFAULT_TAX_RATE_PERCENT
    return Decimal(tax_rate.rate or 0)


def format_money(value):
    return format(money(value), ".2f")


identity_validator = RegexValidator(
    regex=r"^\d{13}$",
    message="La identidad hondureña debe contener 13 dígitos.",
)

rtn_validator = RegexValidator(
    regex=r"^\d{14}$",
    message="El RTN debe contener 14 dígitos.",
)

phone_validator = RegexValidator(
    regex=r"^[0-9+\-\s]{8,20}$",
    message="Ingrese un número de teléfono válido.",
)


# =========================================================
# BASES
# =========================================================


class AuditModel(models.Model):
    user_creation = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
    )
    user_updated = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated",
    )
    date_creation = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# =========================================================
# CATALOGOS
# =========================================================


class Category(AuditModel):
    organization = models.ForeignKey(
        'user.Organization',
        on_delete=models.CASCADE,
        related_name='categories',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=150, verbose_name='Nombre')
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name='Descripción')
    # Compatibilidad con código anterior que usaba `desc`
    desc = models.CharField(max_length=255, null=True, blank=True, verbose_name='Descripción')
    is_active = models.BooleanField(default=True, verbose_name='Activo')

    def __str__(self):
        return self.name

    def toJSON(self):
        return model_to_dict(
            self,
            exclude=['user_creation', 'user_updated', 'date_creation', 'date_updated']
        )

    def save(self, *args, **kwargs):
        # Mantener sincronizados `description` y `desc` para compatibilidad
        if not self.description and self.desc:
            self.description = self.desc
        elif self.description and not self.desc:
            self.desc = self.description
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'name'],
                name='uniq_category_name_per_org',
            ),
        ]


class Supplier(AuditModel):
    organization = models.ForeignKey(
        'user.Organization',
        on_delete=models.CASCADE,
        related_name='suppliers',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=200, verbose_name='Proveedor')
    rtn = models.CharField(max_length=14, null=True, blank=True, validators=[rtn_validator], verbose_name='RTN')
    contact_name = models.CharField(max_length=150, null=True, blank=True, verbose_name='Contacto')
    phone = models.CharField(max_length=20, null=True, blank=True, validators=[phone_validator], verbose_name='Teléfono')
    email = models.EmailField(null=True, blank=True, verbose_name='Correo')
    address = models.CharField(max_length=255, null=True, blank=True, verbose_name='Dirección')
    is_active = models.BooleanField(default=True, verbose_name='Activo')

    def __str__(self):
        return self.name

    def toJSON(self):
        return model_to_dict(
            self,
            exclude=['user_creation', 'user_updated', 'date_creation', 'date_updated']
        )

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'name'],
                name='uniq_supplier_name_per_org',
            ),
        ]


class Client(AuditModel):
    GENDER_CHOICES = (
        ('male', 'Masculino'),
        ('female', 'Femenino'),
        ('other', 'Otro'),
    )

    organization = models.ForeignKey(
        'user.Organization',
        on_delete=models.CASCADE,
        related_name='clients',
        null=True,
        blank=True,
    )
    names = models.CharField(max_length=150, verbose_name='Nombres')
    surnames = models.CharField(max_length=150, verbose_name='Apellidos')
    dni = models.CharField(
        max_length=13,
        null=True,
        blank=True,
        validators=[identity_validator],
        verbose_name='Identidad',
    )
    rtn = models.CharField(
        max_length=14,
        null=True,
        blank=True,
        validators=[rtn_validator],
        verbose_name='RTN',
    )
    date_birthday = models.DateField(null=True, blank=True, verbose_name='Fecha de nacimiento')
    address = models.CharField(max_length=255, null=True, blank=True, verbose_name='Dirección')
    phone = models.CharField(max_length=20, null=True, blank=True, validators=[phone_validator], verbose_name='Teléfono')
    email = models.EmailField(null=True, blank=True, verbose_name='Correo')
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='male', verbose_name='Sexo')
    credit_limit = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Límite de crédito')
    is_credit_customer = models.BooleanField(default=False, verbose_name='Cliente a crédito')
    is_active = models.BooleanField(default=True, verbose_name='Activo')

    def get_full_name(self):
        return f'{self.names} {self.surnames}'.strip()

    def __str__(self):
        return self.get_full_name()

    def toJSON(self):
        item = model_to_dict(
            self,
            exclude=['user_creation', 'user_updated', 'date_creation', 'date_updated'],
        )
        item['full_name'] = self.get_full_name()
        item['credit_limit'] = format_money(self.credit_limit)
        return item

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'dni'],
                name='uniq_client_dni_per_org',
                condition=models.Q(dni__isnull=False),
            ),
            models.UniqueConstraint(
                fields=['organization', 'rtn'],
                name='uniq_client_rtn_per_org',
                condition=models.Q(rtn__isnull=False),
            ),
        ]


class TaxRate(AuditModel):
    organization = models.ForeignKey(
        'user.Organization',
        on_delete=models.CASCADE,
        related_name='tax_rates',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100, verbose_name='Nombre')
    rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Porcentaje')
    code = models.CharField(max_length=20, default='EXENTO', verbose_name='Código')
    is_default = models.BooleanField(default=False, verbose_name='Predeterminado')
    is_active = models.BooleanField(default=True, verbose_name='Activo')

    def __str__(self):
        return f'{self.name} ({self.rate}%)'

    class Meta:
        verbose_name = 'Tasa de impuesto'
        verbose_name_plural = 'Tasas de impuesto'
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'code'],
                name='uniq_tax_code_per_org',
            ),
        ]


class Product(AuditModel):
    UNIT_CHOICES = (
        ('unidad', 'Unidad'),
        ('caja', 'Caja'),
        ('paquete', 'Paquete'),
        ('docena', 'Docena'),
        ('libra', 'Libra'),
        ('kilo', 'Kilo'),
        ('litro', 'Litro'),
        ('metro', 'Metro'),
    )

    organization = models.ForeignKey(
        'user.Organization',
        on_delete=models.CASCADE,
        related_name='products',
        null=True,
        blank=True,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='Categoría',
    )
    # Campo mantenido para compatibilidad con código previo (`cat`)
    cat = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products_cat',
        verbose_name='Categoria',
    )
    image = models.ImageField(
        upload_to='product/%Y/%m/%d',
        null=True,
        blank=True,
        verbose_name='Imagen',
    )
    name = models.CharField(max_length=200, verbose_name='Nombre')
    barcode = models.CharField(max_length=100, null=True, blank=True, verbose_name='Código de barras')
    internal_code = models.CharField(max_length=50, null=True, blank=True, verbose_name='Código interno')
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name='Descripción')
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='unidad', verbose_name='Unidad')
    cost = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Costo')
    pvp = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Precio de venta')
    stock = models.IntegerField(default=0, verbose_name='Stock')
    min_stock = models.IntegerField(default=0, verbose_name='Stock mínimo')
    tax_rate = models.ForeignKey(
        TaxRate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='ISV',
    )
    allow_decimal_qty = models.BooleanField(default=False, verbose_name='Permite fracción')
    is_service = models.BooleanField(default=False, verbose_name='Es servicio')
    is_active = models.BooleanField(default=True, verbose_name='Activo')

    @property
    def utility_unit(self):
        return money(self.pvp) - money(self.cost)

    @property
    def stock_alert(self):
        return self.stock <= self.min_stock

    def sync_category_aliases(self):
        if self.category_id and self.cat_id and self.category_id != self.cat_id:
            self.cat_id = self.category_id
        elif self.category_id and not self.cat_id:
            self.cat_id = self.category_id
        elif self.cat_id and not self.category_id:
            self.category_id = self.cat_id

    def clean(self):
        self.sync_category_aliases()

        if self.category and self.organization_id and self.category.organization_id:
            if self.organization_id != self.category.organization_id:
                raise ValidationError({'category': 'La categoría no pertenece a la misma organización.'})

        if self.tax_rate and self.organization_id and self.tax_rate.organization_id:
            if self.organization_id != self.tax_rate.organization_id:
                raise ValidationError({'tax_rate': 'La tasa de impuesto no pertenece a la misma organización.'})

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.sync_category_aliases()
        super().save(*args, **kwargs)

    def toJSON(self):
        item = model_to_dict(
            self,
            exclude=['user_creation', 'user_updated', 'date_creation', 'date_updated'],
        )
        # Exponer `cat` para compatibilidad; preferir `category` cuando exista
        cat_obj = self.category or self.cat
        item['cat'] = cat_obj.toJSON() if getattr(cat_obj, 'toJSON', None) else {'id': '', 'name': 'Sin categoria'}
        item['image'] = self.image.url if self.image else ''
        item['cost'] = format_money(self.cost)
        item['pvp'] = format_money(self.pvp)
        item['utility_unit'] = format_money(self.utility_unit)
        item['stock_alert'] = self.stock_alert
        item['tax_rate'] = format(effective_tax_rate_percent(self.tax_rate), ".2f")
        return item

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'name'],
                name='uniq_product_name_per_org',
            ),
            models.UniqueConstraint(
                fields=['organization', 'barcode'],
                name='uniq_product_barcode_per_org',
                condition=models.Q(barcode__isnull=False),
            ),
            models.UniqueConstraint(
                fields=['organization', 'internal_code'],
                name='uniq_product_internal_code_per_org',
                condition=models.Q(internal_code__isnull=False),
            ),
        ]
        indexes = [
            models.Index(fields=['organization', 'name']),
            models.Index(fields=['organization', 'barcode']),
            models.Index(fields=['organization', 'internal_code']),
        ]


# =========================================================
# FACTURACION HONDURAS
# =========================================================


class FiscalData(AuditModel):
    """
    Configuración fiscal por organización.
    """
    organization = models.OneToOneField(
        'user.Organization',
        on_delete=models.CASCADE,
        related_name='fiscal_data',
    )
    business_name = models.CharField(max_length=255, verbose_name='Razón social')
    trade_name = models.CharField(max_length=255, null=True, blank=True, verbose_name='Nombre comercial')
    rtn = models.CharField(max_length=14, validators=[rtn_validator], verbose_name='RTN')
    address = models.CharField(max_length=255, verbose_name='Dirección fiscal')
    phone = models.CharField(max_length=20, null=True, blank=True, validators=[phone_validator], verbose_name='Teléfono')
    email = models.EmailField(null=True, blank=True, verbose_name='Correo')
    cai = models.CharField(max_length=50, null=True, blank=True, verbose_name='CAI vigente')
    cai_start_date = models.DateField(null=True, blank=True, verbose_name='Inicio CAI')
    cai_end_date = models.DateField(null=True, blank=True, verbose_name='Fin CAI')
    invoice_prefix = models.CharField(max_length=20, default='001-001-01-', verbose_name='Prefijo fiscal')
    invoice_range_start = models.BigIntegerField(default=1, verbose_name='Rango inicial')
    invoice_range_end = models.BigIntegerField(default=99999999, verbose_name='Rango final')
    next_invoice_number = models.BigIntegerField(default=1, verbose_name='Siguiente número')
    cash_sale_legend = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Leyenda de factura',
    )

    def next_invoice(self):
        if self.next_invoice_number > self.invoice_range_end:
            raise ValidationError('Se agotó el rango fiscal autorizado.')
        current = self.next_invoice_number
        self.next_invoice_number += 1
        self.save(update_fields=['next_invoice_number'])
        return f'{self.invoice_prefix}{str(current).zfill(8)}'

    def clean(self):
        if self.cai_start_date and self.cai_end_date and self.cai_start_date > self.cai_end_date:
            raise ValidationError({'cai_end_date': 'La fecha final del CAI no puede ser menor que la inicial.'})
        if self.invoice_range_start > self.invoice_range_end:
            raise ValidationError({'invoice_range_end': 'El rango final debe ser mayor o igual al inicial.'})

    def __str__(self):
        return self.business_name

    class Meta:
        verbose_name = 'Datos fiscales'
        verbose_name_plural = 'Datos fiscales'


# =========================================================
# CAJA
# =========================================================


class CashSession(AuditModel):
    STATUS_CHOICES = (
        ('open', 'Abierta'),
        ('closed', 'Cerrada'),
    )

    organization = models.ForeignKey(
        'user.Organization',
        on_delete=models.CASCADE,
        related_name='cash_sessions',
    )
    user = models.ForeignKey(
        'user.User',
        on_delete=models.PROTECT,
        related_name='cash_sessions',
        verbose_name='Usuario',
    )
    opened_at = models.DateTimeField(default=timezone.now, verbose_name='Fecha apertura')
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name='Fecha cierre')
    opening_amount = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Monto apertura')
    closing_amount = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Monto cierre')
    expected_amount = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Monto esperado')
    difference = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Diferencia')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open', verbose_name='Estado')
    notes = models.CharField(max_length=255, null=True, blank=True, verbose_name='Observación')

    def __str__(self):
        return f'Caja #{self.id} - {self.user} - {self.get_status_display()}'

    def recalculate(self):
        total_movements = self.movements.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        self.expected_amount = money(self.opening_amount) + money(total_movements)
        self.difference = money(self.closing_amount) - money(self.expected_amount)
        self.save(update_fields=['expected_amount', 'difference'])

    def close_session(self, closing_amount):
        self.closing_amount = money(closing_amount)
        self.closed_at = timezone.now()
        self.status = 'closed'
        self.recalculate()
        self.save(update_fields=['closing_amount', 'closed_at', 'status', 'expected_amount', 'difference'])

    class Meta:
        verbose_name = 'Caja'
        verbose_name_plural = 'Cajas'
        ordering = ['-id']


class CashMovement(AuditModel):
    TYPE_CHOICES = (
        ('sale', 'Venta'),
        ('income', 'Ingreso'),
        ('expense', 'Egreso'),
        ('opening', 'Apertura'),
        ('closing', 'Cierre'),
        ('refund', 'Reembolso'),
    )

    organization = models.ForeignKey(
        'user.Organization',
        on_delete=models.CASCADE,
        related_name='cash_movements',
    )
    cash_session = models.ForeignKey(
        CashSession,
        on_delete=models.CASCADE,
        related_name='movements',
    )
    movement_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='Tipo')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Monto')
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name='Descripción')
    reference = models.CharField(max_length=100, null=True, blank=True, verbose_name='Referencia')

    def __str__(self):
        return f'{self.get_movement_type_display()} - {format_money(self.amount)}'

    class Meta:
        verbose_name = 'Movimiento de caja'
        verbose_name_plural = 'Movimientos de caja'
        ordering = ['-id']


# =========================================================
# INVENTARIO
# =========================================================


class InventoryMovement(AuditModel):
    MOVEMENT_CHOICES = (
        ('purchase', 'Compra'),
        ('sale', 'Venta'),
        ('adjustment_in', 'Ajuste Entrada'),
        ('adjustment_out', 'Ajuste Salida'),
        ('sale_cancel', 'Anulación venta'),
        ('purchase_cancel', 'Anulación compra'),
        ('return_sale', 'Devolución cliente'),
        ('return_purchase', 'Devolución proveedor'),
    )

    organization = models.ForeignKey(
        'user.Organization',
        on_delete=models.CASCADE,
        related_name='inventory_movements',
        null=True,
        blank=True,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='movements',
    )
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_CHOICES, verbose_name='Tipo')
    quantity = models.IntegerField(verbose_name='Cantidad')
    stock_before = models.IntegerField(default=0, verbose_name='Stock anterior')
    stock_after = models.IntegerField(default=0, verbose_name='Stock actual')
    description = models.CharField(max_length=255, blank=True, null=True, verbose_name='Descripción')
    reference = models.CharField(max_length=100, blank=True, null=True, verbose_name='Referencia')
    date_joined = models.DateTimeField(default=timezone.now, verbose_name='Fecha')

    def clean(self):
        if self.product and self.organization_id and self.product.organization_id:
            if self.organization_id != self.product.organization_id:
                raise ValidationError({'product': 'El producto no pertenece a la misma organización.'})

    def __str__(self):
        return f'{self.get_movement_type_display()} - {self.product.name} - {self.quantity}'

    def toJSON(self):
        item = model_to_dict(
            self,
            exclude=['user_creation', 'user_updated', 'date_creation', 'date_updated'],
        )
        item['product'] = self.product.toJSON()
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d %H:%M:%S')
        return item

    class Meta:
        verbose_name = 'Movimiento de inventario'
        verbose_name_plural = 'Movimientos de inventario'
        ordering = ['-id']


# =========================================================
# COMPRAS
# =========================================================


class Purchase(AuditModel):
    STATUS_CHOICES = (
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmada'),
        ('cancelled', 'Anulada'),
    )

    PAYMENT_TERM_CHOICES = (
        ('cash', 'Contado'),
        ('credit', 'Crédito'),
    )

    organization = models.ForeignKey(
        'user.Organization',
        on_delete=models.CASCADE,
        related_name='purchases',
        null=True,
        blank=True,
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchases',
        verbose_name='Proveedor',
    )
    number = models.CharField(max_length=50, null=True, blank=True, verbose_name='Número de compra')
    supplier_invoice = models.CharField(max_length=100, null=True, blank=True, verbose_name='Factura proveedor')
    date_joined = models.DateField(default=timezone.now, verbose_name='Fecha de compra')
    payment_term = models.CharField(max_length=10, choices=PAYMENT_TERM_CHOICES, default='cash', verbose_name='Condición')
    due_date = models.DateField(null=True, blank=True, verbose_name='Vence')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft', verbose_name='Estado')
    subtotal = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    tax_total = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='ISV')
    # Campo de compatibilidad con código previo que usa `iva`
    iva = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='IVA')
    total = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Pagado')
    balance = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Saldo')
    observation = models.CharField(max_length=255, blank=True, null=True, verbose_name='Observación')
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f'Compra #{self.id} - {self.supplier.name}'

    def clean(self):
        if self.supplier and self.organization_id and self.supplier.organization_id:
            if self.organization_id != self.supplier.organization_id:
                raise ValidationError({'supplier': 'El proveedor no pertenece a la misma organización.'})

    def recalculate_totals(self):
        details = self.details.all()
        subtotal = Decimal('0.00')
        tax_total = Decimal('0.00')

        for d in details:
            subtotal += money(d.subtotal_before_tax)
            tax_total += money(d.tax_amount)

        self.subtotal = money(subtotal)
        self.tax_total = money(tax_total)
        # Mantener compatibilidad con `iva`
        self.iva = self.tax_total
        self.total = money(self.subtotal + self.tax_total)
        self.balance = money(self.total - self.amount_paid)
        self.save(update_fields=['subtotal', 'tax_total', 'iva', 'total', 'balance'])

    @transaction.atomic
    def confirm(self, user=None):
        if self.status != 'draft':
            raise ValidationError('Solo se pueden confirmar compras en borrador.')

        for detail in self.details.select_related('prod').all():
            stock_before = detail.prod.stock
            detail.prod.stock += detail.cant
            detail.prod.cost = detail.cost
            detail.prod.save(update_fields=['stock', 'cost'])

            InventoryMovement.objects.create(
                organization=self.organization,
                product=detail.prod,
                movement_type='purchase',
                quantity=detail.cant,
                stock_before=stock_before,
                stock_after=detail.prod.stock,
                description=f'Entrada por compra #{self.id}',
                reference=f'PUR-{self.id}',
                user_creation=user,
                user_updated=user,
            )

        self.status = 'confirmed'
        self.confirmed_at = timezone.now()
        if user:
            self.user_updated = user
        self.save(update_fields=['status', 'confirmed_at', 'user_updated'])

    @transaction.atomic
    def cancel(self, reason='', user=None):
        if self.status != 'confirmed':
            raise ValidationError('Solo se pueden anular compras confirmadas.')

        for detail in self.details.select_related('prod').all():
            stock_before = detail.prod.stock
            new_stock = max(0, detail.prod.stock - detail.cant)
            detail.prod.stock = new_stock
            detail.prod.save(update_fields=['stock'])

            InventoryMovement.objects.create(
                organization=self.organization,
                product=detail.prod,
                movement_type='purchase_cancel',
                quantity=detail.cant,
                stock_before=stock_before,
                stock_after=detail.prod.stock,
                description=f'Anulación compra #{self.id}',
                reference=f'PUR-{self.id}-CAN',
                user_creation=user,
                user_updated=user,
            )

        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.cancellation_reason = reason
        if user:
            self.user_updated = user
        self.save(update_fields=['status', 'cancelled_at', 'cancellation_reason', 'user_updated'])

    def toJSON(self):
        item = model_to_dict(self, exclude=['user_creation', 'user_updated', 'date_creation', 'date_updated'])
        item['subtotal'] = format_money(self.subtotal)
        item['tax_total'] = format_money(self.tax_total)
        item['total'] = format_money(self.total)
        item['amount_paid'] = format_money(self.amount_paid)
        item['balance'] = format_money(self.balance)
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['details'] = [i.toJSON() for i in self.details.all()]
        return item

    class Meta:
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'
        ordering = ['id']
        indexes = [
            models.Index(fields=['organization', 'date_joined']),
            models.Index(fields=['organization', 'status']),
        ]


class DetPurchase(models.Model):
    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name='details',
    )
    prod = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='purchase_details',
    )
    cost = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Costo')
    cant = models.IntegerField(default=1, validators=[MinValueValidator(1)], verbose_name='Cantidad')
    tax_rate = models.ForeignKey(
        TaxRate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_details',
        verbose_name='ISV',
    )
    subtotal_before_tax = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Subtotal')
    tax_amount = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Impuesto')
    subtotal = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Total línea')

    def __str__(self):
        return f'{self.prod.name} - {self.cant}'

    def clean(self):
        if self.purchase and self.prod and self.purchase.organization_id and self.prod.organization_id:
            if self.purchase.organization_id != self.prod.organization_id:
                raise ValidationError({'prod': 'El producto no pertenece a la misma organización de la compra.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        self.tax_rate = self.tax_rate or self.prod.tax_rate
        self.subtotal_before_tax = money(self.cost) * self.cant
        rate = effective_tax_rate_percent(self.tax_rate)
        self.tax_amount = calculate_tax(self.subtotal_before_tax, rate)
        self.subtotal = money(self.subtotal_before_tax + self.tax_amount)
        super().save(*args, **kwargs)
        self.purchase.recalculate_totals()

    def delete(self, *args, **kwargs):
        purchase = self.purchase
        super().delete(*args, **kwargs)
        purchase.recalculate_totals()

    def toJSON(self):
        item = model_to_dict(self, exclude=['purchase'])
        item['prod'] = self.prod.toJSON()
        item['cost'] = format_money(self.cost)
        item['subtotal_before_tax'] = format_money(self.subtotal_before_tax)
        item['tax_amount'] = format_money(self.tax_amount)
        item['subtotal'] = format_money(self.subtotal)
        return item

    class Meta:
        verbose_name = 'Detalle de compra'
        verbose_name_plural = 'Detalles de compra'
        ordering = ['id']


# =========================================================
# VENTAS
# =========================================================


class Sale(AuditModel):
    STATUS_CHOICES = (
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmada'),
        ('cancelled', 'Anulada'),
    )

    DOCUMENT_TYPE_CHOICES = (
        ('invoice', 'Factura'),
        ('proforma', 'Proforma'),
        ('receipt', 'Recibo'),
    )

    PAYMENT_TERM_CHOICES = (
        ('cash', 'Contado'),
        ('credit', 'Crédito'),
        ('mixed', 'Mixto'),
    )

    organization = models.ForeignKey(
        'user.Organization',
        on_delete=models.CASCADE,
        related_name='sales',
        null=True,
        blank=True,
    )
    cli = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name='sales',
        verbose_name='Cliente',
    )
    cash_session = models.ForeignKey(
        CashSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales',
        verbose_name='Caja',
    )

    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES, default='invoice', verbose_name='Documento')
    number = models.CharField(max_length=50, null=True, blank=True, verbose_name='Número')
    cai = models.CharField(max_length=50, null=True, blank=True, verbose_name='CAI')
    issue_deadline = models.DateField(null=True, blank=True, verbose_name='Fecha límite CAI')

    payment_term = models.CharField(max_length=10, choices=PAYMENT_TERM_CHOICES, default='cash', verbose_name='Condición')
    date_joined = models.DateField(default=timezone.now, verbose_name='Fecha de venta')
    due_date = models.DateField(null=True, blank=True, verbose_name='Vence')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft', verbose_name='Estado')

    subtotal = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    discount = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Descuento')
    tax_total = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='ISV')
    # Campo de compatibilidad con código previo que usa `iva`
    iva = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='IVA')
    total = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Pagado')
    balance = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Saldo')
    profit = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Ganancia')
    observation = models.CharField(max_length=255, blank=True, null=True, verbose_name='Observación')

    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f'Venta #{self.id} - {self.cli.get_full_name()}'

    def clean(self):
        if self.cli and self.organization_id and self.cli.organization_id:
            if self.organization_id != self.cli.organization_id:
                raise ValidationError({'cli': 'El cliente no pertenece a la misma organización.'})

        if self.cash_session and self.organization_id and self.cash_session.organization_id:
            if self.organization_id != self.cash_session.organization_id:
                raise ValidationError({'cash_session': 'La caja no pertenece a la misma organización.'})

    def recalculate_totals(self):
        details = self.details.all()
        subtotal = Decimal('0.00')
        tax_total = Decimal('0.00')
        profit = Decimal('0.00')

        for d in details:
            subtotal += money(d.subtotal_before_tax)
            tax_total += money(d.tax_amount)
            profit += money(d.profit)

        self.subtotal = money(subtotal)
        self.tax_total = money(tax_total)
        # Sincronizar con `iva` para compatibilidad
        self.iva = self.tax_total
        gross_total = money(self.subtotal + self.tax_total)
        self.total = money(gross_total - money(self.discount))
        self.profit = money(profit - money(self.discount))
        self.balance = money(self.total - self.amount_paid)
        self.save(update_fields=['subtotal', 'tax_total', 'iva', 'total', 'profit', 'balance'])

    # Compatibilidad con código previo que llamaba `calculate_totals(iva=...)`
    def calculate_totals(self, iva=None):
        self.recalculate_totals()
        if iva is None:
            return self

        explicit_tax = money(iva)
        self.tax_total = explicit_tax
        self.iva = explicit_tax
        gross_total = money(self.subtotal + self.tax_total)
        self.total = money(gross_total - money(self.discount))
        self.balance = money(self.total - self.amount_paid)
        self.save(update_fields=['tax_total', 'iva', 'total', 'balance'])
        return self

    def _assign_fiscal_number(self):
        if self.document_type != 'invoice' or self.number:
            return

        fiscal = getattr(self.organization, 'fiscal_data', None)
        if not fiscal:
            raise ValidationError('La organización no tiene datos fiscales configurados.')

        if fiscal.cai_end_date and self.date_joined > fiscal.cai_end_date:
            raise ValidationError('El CAI vigente está vencido.')

        self.number = fiscal.next_invoice()
        self.cai = fiscal.cai
        self.issue_deadline = fiscal.cai_end_date

    @transaction.atomic
    def confirm(self, user=None):
        if self.status != 'draft':
            raise ValidationError('Solo se pueden confirmar ventas en borrador.')

        self._assign_fiscal_number()

        for detail in self.details.select_related('prod').all():
            if not detail.prod.is_service:
                if detail.cant > detail.prod.stock:
                    raise ValidationError(f'Stock insuficiente para {detail.prod.name}. Disponible: {detail.prod.stock}')

        for detail in self.details.select_related('prod').all():
            if detail.prod.is_service:
                continue

            stock_before = detail.prod.stock
            detail.prod.stock -= detail.cant
            detail.prod.save(update_fields=['stock'])

            InventoryMovement.objects.create(
                organization=self.organization,
                product=detail.prod,
                movement_type='sale',
                quantity=detail.cant,
                stock_before=stock_before,
                stock_after=detail.prod.stock,
                description=f'Salida por venta #{self.id}',
                reference=f'SAL-{self.id}',
                user_creation=user,
                user_updated=user,
            )

        self.status = 'confirmed'
        self.confirmed_at = timezone.now()
        if user:
            self.user_updated = user
        self.save(update_fields=['number', 'cai', 'issue_deadline', 'status', 'confirmed_at', 'user_updated'])

        if self.cash_session and self.amount_paid > 0:
            CashMovement.objects.create(
                organization=self.organization,
                cash_session=self.cash_session,
                movement_type='sale',
                amount=self.amount_paid,
                description=f'Cobro venta #{self.id}',
                reference=f'SAL-{self.id}',
                user_creation=user,
                user_updated=user,
            )
            self.cash_session.recalculate()

    @transaction.atomic
    def cancel(self, reason='', user=None):
        if self.status != 'confirmed':
            raise ValidationError('Solo se pueden anular ventas confirmadas.')

        for detail in self.details.select_related('prod').all():
            if detail.prod.is_service:
                continue

            stock_before = detail.prod.stock
            detail.prod.stock += detail.cant
            detail.prod.save(update_fields=['stock'])

            InventoryMovement.objects.create(
                organization=self.organization,
                product=detail.prod,
                movement_type='sale_cancel',
                quantity=detail.cant,
                stock_before=stock_before,
                stock_after=detail.prod.stock,
                description=f'Anulación venta #{self.id}',
                reference=f'SAL-{self.id}-CAN',
                user_creation=user,
                user_updated=user,
            )

        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.cancellation_reason = reason
        if user:
            self.user_updated = user
        self.save(update_fields=['status', 'cancelled_at', 'cancellation_reason', 'user_updated'])

    def register_payment(self, amount):
        self.amount_paid = money(self.amount_paid) + money(amount)
        self.balance = money(self.total - self.amount_paid)
        self.save(update_fields=['amount_paid', 'balance'])

    def toJSON(self):
        item = model_to_dict(self, exclude=['user_creation', 'user_updated', 'date_creation', 'date_updated'])
        item['cli'] = self.cli.toJSON() if self.cli_id else None
        item['subtotal'] = format_money(self.subtotal)
        item['discount'] = format_money(self.discount)
        item['tax_total'] = format_money(self.tax_total)
        item['total'] = format_money(self.total)
        item['amount_paid'] = format_money(self.amount_paid)
        item['balance'] = format_money(self.balance)
        item['profit'] = format_money(self.profit)
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['details'] = [i.toJSON() for i in self.details.all()]
        return item

    class Meta:
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering = ['id']
        indexes = [
            models.Index(fields=['organization', 'date_joined']),
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'number']),
        ]


class DetSale(models.Model):
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='details',
    )
    prod = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='sale_details',
    )
    price = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Precio venta')
    cost = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Costo')
    cant = models.IntegerField(default=1, validators=[MinValueValidator(1)], verbose_name='Cantidad')
    discount = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Descuento línea')
    tax_rate = models.ForeignKey(
        TaxRate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sale_details',
        verbose_name='ISV',
    )
    subtotal_before_tax = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Subtotal')
    tax_amount = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Impuesto')
    subtotal = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Total línea')
    profit = models.DecimalField(default=0, max_digits=12, decimal_places=2, verbose_name='Ganancia')

    def __str__(self):
        return f'{self.prod.name} - {self.cant}'

    def clean(self):
        if self.sale and self.prod and self.sale.organization_id and self.prod.organization_id:
            if self.sale.organization_id != self.prod.organization_id:
                raise ValidationError({'prod': 'El producto no pertenece a la misma organización de la venta.'})

        if self.sale and self.sale.status != 'draft':
            raise ValidationError('No se pueden editar detalles en una venta que no está en borrador.')

    def save(self, *args, **kwargs):
        self.full_clean()

        if self.cost == Decimal('0.00'):
            self.cost = self.prod.cost

        if self.price == Decimal('0.00'):
            self.price = self.prod.pvp

        self.tax_rate = self.tax_rate or self.prod.tax_rate

        base = (money(self.price) * self.cant) - money(self.discount)
        if base < 0:
            raise ValidationError({'discount': 'El descuento no puede ser mayor al subtotal de la línea.'})

        rate = effective_tax_rate_percent(self.tax_rate)
        self.subtotal_before_tax = money(base)
        self.tax_amount = calculate_tax(self.subtotal_before_tax, rate)
        self.subtotal = money(self.subtotal_before_tax + self.tax_amount)
        self.profit = money((money(self.price) - money(self.cost)) * self.cant - money(self.discount))

        super().save(*args, **kwargs)
        self.sale.recalculate_totals()

    def delete(self, *args, **kwargs):
        sale = self.sale
        super().delete(*args, **kwargs)
        sale.recalculate_totals()

    def toJSON(self):
        item = model_to_dict(self, exclude=['sale'])
        item['prod'] = self.prod.toJSON()
        item['price'] = format_money(self.price)
        item['cost'] = format_money(self.cost)
        item['discount'] = format_money(self.discount)
        item['subtotal_before_tax'] = format_money(self.subtotal_before_tax)
        item['tax_amount'] = format_money(self.tax_amount)
        item['subtotal'] = format_money(self.subtotal)
        item['profit'] = format_money(self.profit)
        return item

    class Meta:
        verbose_name = 'Detalle de venta'
        verbose_name_plural = 'Detalles de venta'
        ordering = ['id']


# =========================================================
# PAGOS Y CREDITO
# =========================================================


class SalePayment(AuditModel):
    METHOD_CHOICES = (
        ('cash', 'Efectivo'),
        ('transfer', 'Transferencia'),
        ('card', 'Tarjeta'),
        ('mobile', 'Pago móvil'),
        ('check', 'Cheque'),
        ('credit_note', 'Nota de crédito'),
    )

    organization = models.ForeignKey(
        'user.Organization',
        on_delete=models.CASCADE,
        related_name='sale_payments',
    )
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='payments',
    )
    cash_session = models.ForeignKey(
        CashSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
    )
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, verbose_name='Método')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Monto')
    reference = models.CharField(max_length=100, null=True, blank=True, verbose_name='Referencia')
    notes = models.CharField(max_length=255, null=True, blank=True, verbose_name='Observación')
    paid_at = models.DateTimeField(default=timezone.now, verbose_name='Fecha de pago')

    def clean(self):
        if self.sale and self.organization_id and self.sale.organization_id:
            if self.organization_id != self.sale.organization_id:
                raise ValidationError({'sale': 'La venta no pertenece a la misma organización.'})

    @transaction.atomic
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            self.sale.register_payment(self.amount)

            if self.cash_session and self.method == 'cash':
                CashMovement.objects.create(
                    organization=self.organization,
                    cash_session=self.cash_session,
                    movement_type='income',
                    amount=self.amount,
                    description=f'Pago recibido venta #{self.sale.id}',
                    reference=self.reference or f'SAL-{self.sale.id}',
                    user_creation=self.user_creation,
                    user_updated=self.user_updated,
                )
                self.cash_session.recalculate()

    def __str__(self):
        return f'Pago venta #{self.sale.id} - {self.get_method_display()}'

    class Meta:
        verbose_name = 'Pago de venta'
        verbose_name_plural = 'Pagos de venta'
        ordering = ['-id']


class PurchasePayment(AuditModel):
    METHOD_CHOICES = (
        ('cash', 'Efectivo'),
        ('transfer', 'Transferencia'),
        ('card', 'Tarjeta'),
        ('check', 'Cheque'),
    )

    organization = models.ForeignKey(
        'user.Organization',
        on_delete=models.CASCADE,
        related_name='purchase_payments',
    )
    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name='payments',
    )
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, verbose_name='Método')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Monto')
    reference = models.CharField(max_length=100, null=True, blank=True, verbose_name='Referencia')
    notes = models.CharField(max_length=255, null=True, blank=True, verbose_name='Observación')
    paid_at = models.DateTimeField(default=timezone.now, verbose_name='Fecha de pago')

    @transaction.atomic
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.purchase.amount_paid = money(self.purchase.amount_paid) + money(self.amount)
            self.purchase.balance = money(self.purchase.total - self.purchase.amount_paid)
            self.purchase.save(update_fields=['amount_paid', 'balance'])

    def __str__(self):
        return f'Pago compra #{self.purchase.id} - {self.get_method_display()}'

    class Meta:
        verbose_name = 'Pago de compra'
        verbose_name_plural = 'Pagos de compra'
        ordering = ['-id']
