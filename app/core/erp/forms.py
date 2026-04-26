from datetime import datetime

from django import forms
from django.forms import DateInput, HiddenInput, ModelForm, NumberInput, Select, TextInput, Textarea

from app.core.erp.models import (
    CashMovement,
    CashSession,
    Category,
    Client,
    FiscalData,
    Product,
    Purchase,
    Sale,
    Supplier,
    TaxRate,
)


class RequestModelForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def get_current_organization(self):
        if self.request and self.request.user.is_authenticated:
            return self.request.user.get_current_organization()
        return None

    def prepare_instance(self, instance):
        return instance

    def save_model(self, commit=True):
        instance = super().save(commit=False)
        current_organization = self.get_current_organization()
        current_user = self.request.user if self.request and self.request.user.is_authenticated else None

        if hasattr(instance, 'organization_id') and not instance.organization_id:
            instance.organization = current_organization

        if hasattr(instance, 'user_creation_id') and current_user and not instance.pk:
            instance.user_creation = current_user

        if hasattr(instance, 'user_updated_id') and current_user:
            instance.user_updated = current_user

        instance = self.prepare_instance(instance)
        instance.full_clean()

        if commit:
            instance.save()
            self.save_m2m()

        return instance

    def save(self, commit=True):
        data = {}
        try:
            if self.is_valid():
                instance = self.save_model(commit=commit)
                if hasattr(instance, 'toJSON'):
                    return instance.toJSON()
                data['success'] = True
                data['id'] = instance.pk
            else:
                data['error'] = self.errors
        except Exception as e:
            data['error'] = str(e)
        return data


class CategoryForm(RequestModelForm):
    class Meta:
        model = Category
        fields = ('name', 'description', 'desc', 'is_active')
        widgets = {
            'name': TextInput(attrs={'placeholder': 'Ingrese un nombre', 'autofocus': True}),
            'description': Textarea(
                attrs={
                    'placeholder': 'Ingrese una descripcion',
                    'rows': 3,
                }
            ),
            'desc': HiddenInput(),
        }

    def prepare_instance(self, instance):
        instance.desc = instance.description or instance.desc
        instance.description = instance.description or instance.desc
        return instance


class SupplierForm(RequestModelForm):
    class Meta:
        model = Supplier
        fields = ('name', 'rtn', 'contact_name', 'phone', 'email', 'address', 'is_active')
        widgets = {
            'name': TextInput(attrs={'placeholder': 'Ingrese el proveedor', 'autofocus': True}),
            'rtn': TextInput(attrs={'placeholder': 'Ingrese el RTN'}),
            'contact_name': TextInput(attrs={'placeholder': 'Ingrese el contacto'}),
            'phone': TextInput(attrs={'placeholder': 'Ingrese el telefono'}),
            'email': TextInput(attrs={'placeholder': 'Ingrese el correo'}),
            'address': Textarea(attrs={'placeholder': 'Ingrese la direccion', 'rows': 2}),
        }


class TaxRateForm(RequestModelForm):
    class Meta:
        model = TaxRate
        fields = ('name', 'rate', 'code', 'is_default', 'is_active')
        widgets = {
            'name': TextInput(attrs={'placeholder': 'Ingrese el nombre', 'autofocus': True}),
            'rate': NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'code': TextInput(attrs={'placeholder': 'Ejemplo: ISV15'}),
        }

    def save_model(self, commit=True):
        instance = super().save_model(commit=commit)
        if commit and instance.is_default:
            TaxRate.objects.filter(organization=instance.organization).exclude(pk=instance.pk).update(is_default=False)
        return instance


class ProductForm(RequestModelForm):
    class Meta:
        model = Product
        fields = (
            'name',
            'category',
            'cat',
            'image',
            'barcode',
            'internal_code',
            'description',
            'unit',
            'cost',
            'pvp',
            'stock',
            'min_stock',
            'tax_rate',
            'allow_decimal_qty',
            'is_service',
            'is_active',
        )
        widgets = {
            'name': TextInput(attrs={'placeholder': 'Ingrese un nombre', 'autofocus': True}),
            'category': Select(),
            'cat': HiddenInput(),
            'image': forms.ClearableFileInput(attrs={'accept': 'image/*', 'capture': 'environment'}),
            'barcode': TextInput(attrs={'placeholder': 'Ingrese el codigo de barras'}),
            'internal_code': TextInput(attrs={'placeholder': 'Ingrese el codigo interno'}),
            'description': Textarea(attrs={'placeholder': 'Ingrese la descripcion', 'rows': 3}),
            'cost': NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'pvp': NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'stock': NumberInput(attrs={'step': '1', 'min': '0'}),
            'min_stock': NumberInput(attrs={'step': '1', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        organization = self.get_current_organization()
        if organization:
            categories = Category.objects.filter(organization=organization).order_by('name')
            taxes = TaxRate.objects.filter(organization=organization, is_active=True).order_by('name')
            self.fields['category'].queryset = categories
            self.fields['cat'].queryset = categories
            self.fields['tax_rate'].queryset = taxes
        if self.instance and not self.instance.category_id and self.instance.cat_id:
            self.initial['category'] = self.instance.cat_id

    def clean(self):
        cleaned = super().clean()
        for field_name in ('barcode', 'internal_code', 'description'):
            if cleaned.get(field_name) == '':
                cleaned[field_name] = None
        return cleaned

    def prepare_instance(self, instance):
        selected_category = instance.category or instance.cat
        instance.category = selected_category
        instance.cat = selected_category
        instance.barcode = instance.barcode or None
        instance.internal_code = instance.internal_code or None
        instance.description = instance.description or None
        return instance


class ClientForm(RequestModelForm):
    class Meta:
        model = Client
        fields = (
            'names',
            'surnames',
            'dni',
            'rtn',
            'date_birthday',
            'address',
            'phone',
            'email',
            'gender',
            'credit_limit',
            'is_credit_customer',
            'is_active',
        )
        widgets = {
            'names': TextInput(attrs={'placeholder': 'Ingrese sus nombres', 'autofocus': True}),
            'surnames': TextInput(attrs={'placeholder': 'Ingrese sus apellidos'}),
            'dni': TextInput(attrs={'placeholder': 'Ingrese su identidad'}),
            'rtn': TextInput(attrs={'placeholder': 'Ingrese el RTN'}),
            'date_birthday': DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'address': TextInput(attrs={'placeholder': 'Ingrese su direccion'}),
            'phone': TextInput(attrs={'placeholder': 'Ingrese su telefono'}),
            'email': TextInput(attrs={'placeholder': 'Ingrese su correo'}),
            'gender': Select(),
            'credit_limit': NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

    def clean(self):
        cleaned = super().clean()
        for field_name in ('dni', 'rtn', 'date_birthday', 'address', 'phone', 'email'):
            if cleaned.get(field_name) == '':
                cleaned[field_name] = None
        return cleaned

    def prepare_instance(self, instance):
        instance.dni = instance.dni or None
        instance.rtn = instance.rtn or None
        instance.date_birthday = instance.date_birthday or None
        instance.address = instance.address or None
        instance.phone = instance.phone or None
        instance.email = instance.email or None
        return instance


class SaleForm(RequestModelForm):
    class Meta:
        model = Sale
        fields = (
            'cli',
            'cash_session',
            'document_type',
            'payment_term',
            'date_joined',
            'due_date',
            'discount',
            'subtotal',
            'tax_total',
            'iva',
            'total',
            'amount_paid',
            'balance',
            'observation',
        )
        widgets = {
            'cli': Select(attrs={'class': 'form-control select2', 'style': 'width: 100%'}),
            'cash_session': Select(attrs={'class': 'form-control select2', 'style': 'width: 100%'}),
            'document_type': Select(),
            'payment_term': Select(),
            'date_joined': DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'due_date': DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'discount': NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'subtotal': TextInput(attrs={'readonly': True}),
            'tax_total': TextInput(attrs={'readonly': True}),
            'iva': HiddenInput(),
            'total': TextInput(attrs={'readonly': True}),
            'amount_paid': NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'balance': TextInput(attrs={'readonly': True}),
            'observation': Textarea(attrs={'rows': 3, 'placeholder': 'Observaciones de la venta'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and not getattr(self.instance, 'pk', None):
            self.fields['date_joined'].initial = datetime.now().strftime('%Y-%m-%d')
        organization = self.get_current_organization()
        if organization:
            self.fields['cli'].queryset = Client.objects.filter(organization=organization, is_active=True).order_by('names', 'surnames')
            self.fields['cash_session'].queryset = CashSession.objects.filter(
                organization=organization,
                status='open',
            ).order_by('-opened_at')

    def prepare_instance(self, instance):
        instance.tax_total = instance.tax_total or instance.iva
        instance.iva = instance.tax_total or instance.iva
        return instance


class FiscalDataForm(RequestModelForm):
    class Meta:
        model = FiscalData
        fields = (
            'business_name',
            'trade_name',
            'rtn',
            'address',
            'phone',
            'email',
            'cai',
            'cai_start_date',
            'cai_end_date',
            'invoice_prefix',
            'invoice_range_start',
            'invoice_range_end',
            'next_invoice_number',
            'cash_sale_legend',
        )
        widgets = {
            'business_name': TextInput(attrs={'placeholder': 'Ingrese la razon social', 'autofocus': True}),
            'trade_name': TextInput(attrs={'placeholder': 'Ingrese el nombre comercial'}),
            'rtn': TextInput(attrs={'placeholder': 'Ingrese el RTN'}),
            'address': Textarea(attrs={'rows': 2, 'placeholder': 'Ingrese la direccion fiscal'}),
            'phone': TextInput(attrs={'placeholder': 'Ingrese el telefono'}),
            'email': TextInput(attrs={'placeholder': 'Ingrese el correo'}),
            'cai': TextInput(attrs={'placeholder': 'Ingrese el CAI vigente'}),
            'cai_start_date': DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'cai_end_date': DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'invoice_prefix': TextInput(attrs={'placeholder': 'Ejemplo: 001-001-01-'}),
            'invoice_range_start': NumberInput(attrs={'step': '1', 'min': '1'}),
            'invoice_range_end': NumberInput(attrs={'step': '1', 'min': '1'}),
            'next_invoice_number': NumberInput(attrs={'step': '1', 'min': '1'}),
            'cash_sale_legend': Textarea(attrs={'rows': 2, 'placeholder': 'Leyenda para la factura'}),
        }


class CashSessionForm(RequestModelForm):
    class Meta:
        model = CashSession
        fields = ('opening_amount', 'notes')
        widgets = {
            'opening_amount': NumberInput(attrs={'step': '0.01', 'min': '0', 'autofocus': True}),
            'notes': Textarea(attrs={'rows': 2, 'placeholder': 'Observaciones de apertura'}),
        }

    def prepare_instance(self, instance):
        if self.request and self.request.user.is_authenticated:
            instance.user = self.request.user
        return instance


class CashSessionCloseForm(forms.Form):
    closing_amount = forms.DecimalField(
        min_value=0,
        decimal_places=2,
        max_digits=12,
        widget=NumberInput(attrs={'step': '0.01', 'min': '0', 'autofocus': True}),
        label='Monto de cierre',
    )
    notes = forms.CharField(
        required=False,
        widget=Textarea(attrs={'rows': 2, 'placeholder': 'Observaciones de cierre'}),
        label='Observacion',
    )


class CashMovementForm(RequestModelForm):
    class Meta:
        model = CashMovement
        fields = ('cash_session', 'movement_type', 'amount', 'description', 'reference')
        widgets = {
            'cash_session': Select(),
            'movement_type': Select(),
            'amount': NumberInput(attrs={'step': '0.01', 'min': '0', 'autofocus': True}),
            'description': TextInput(attrs={'placeholder': 'Ingrese la descripcion'}),
            'reference': TextInput(attrs={'placeholder': 'Ingrese la referencia'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        organization = self.get_current_organization()
        if organization:
            self.fields['cash_session'].queryset = CashSession.objects.filter(
                organization=organization,
                status='open',
            ).order_by('-opened_at')

    def save_model(self, commit=True):
        instance = super().save_model(commit=commit)
        if commit:
            instance.cash_session.recalculate()
        return instance


class PurchaseForm(RequestModelForm):
    class Meta:
        model = Purchase
        fields = (
            'supplier',
            'number',
            'supplier_invoice',
            'payment_term',
            'date_joined',
            'due_date',
            'subtotal',
            'tax_total',
            'iva',
            'total',
            'amount_paid',
            'balance',
            'observation',
        )
        widgets = {
            'supplier': Select(attrs={'class': 'form-control select2', 'style': 'width: 100%'}),
            'number': TextInput(attrs={'placeholder': 'Ingrese el numero interno'}),
            'supplier_invoice': TextInput(attrs={'placeholder': 'Ingrese la factura del proveedor'}),
            'payment_term': Select(),
            'date_joined': DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'due_date': DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'subtotal': TextInput(attrs={'readonly': True}),
            'tax_total': TextInput(attrs={'readonly': True}),
            'iva': HiddenInput(),
            'total': TextInput(attrs={'readonly': True}),
            'amount_paid': NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'balance': TextInput(attrs={'readonly': True}),
            'observation': Textarea(attrs={'rows': 3, 'placeholder': 'Observaciones de la compra'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and not getattr(self.instance, 'pk', None):
            self.fields['date_joined'].initial = datetime.now().strftime('%Y-%m-%d')
        organization = self.get_current_organization()
        if organization:
            self.fields['supplier'].queryset = Supplier.objects.filter(
                organization=organization,
                is_active=True,
            ).order_by('name')

    def prepare_instance(self, instance):
        instance.tax_total = instance.tax_total or instance.iva
        instance.iva = instance.tax_total or instance.iva
        return instance
