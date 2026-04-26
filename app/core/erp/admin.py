from django.contrib import admin

from app.core.erp.models import (
    CashMovement,
    CashSession,
    Category,
    Client,
    FiscalData,
    InventoryMovement,
    Product,
    Purchase,
    PurchasePayment,
    Sale,
    SalePayment,
    Supplier,
    TaxRate,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'is_active')
    list_filter = ('organization', 'is_active')
    search_fields = ('name', 'description', 'desc')
    ordering = ('name',)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'contact_name', 'phone', 'is_active')
    list_filter = ('organization', 'is_active')
    search_fields = ('name', 'rtn', 'contact_name', 'phone', 'email')
    ordering = ('name',)


@admin.register(TaxRate)
class TaxRateAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'rate', 'code', 'is_default', 'is_active')
    list_filter = ('organization', 'is_default', 'is_active')
    search_fields = ('name', 'code')
    ordering = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'category', 'pvp', 'stock', 'is_active')
    list_filter = ('organization', 'is_active', 'category', 'tax_rate')
    search_fields = ('name', 'barcode', 'internal_code')
    ordering = ('name',)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'organization', 'dni', 'rtn', 'phone', 'is_active')
    list_filter = ('organization', 'gender', 'is_credit_customer', 'is_active')
    search_fields = ('names', 'surnames', 'dni', 'rtn', 'phone')
    ordering = ('names', 'surnames')


@admin.register(FiscalData)
class FiscalDataAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'organization', 'rtn', 'cai', 'invoice_prefix')
    search_fields = ('business_name', 'rtn', 'cai')


@admin.register(CashSession)
class CashSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'organization', 'user', 'opened_at', 'closed_at', 'status', 'expected_amount', 'difference')
    list_filter = ('organization', 'status')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    ordering = ('-opened_at', '-id')


@admin.register(CashMovement)
class CashMovementAdmin(admin.ModelAdmin):
    list_display = ('id', 'organization', 'cash_session', 'movement_type', 'amount', 'reference')
    list_filter = ('organization', 'movement_type')
    search_fields = ('reference', 'description')
    ordering = ('-id',)


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = ('id', 'organization', 'product', 'movement_type', 'quantity', 'stock_before', 'stock_after', 'date_joined')
    list_filter = ('organization', 'movement_type')
    search_fields = ('product__name', 'reference', 'description')
    ordering = ('-date_joined', '-id')


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'organization', 'supplier', 'date_joined', 'status', 'total', 'balance')
    list_filter = ('organization', 'status', 'payment_term')
    search_fields = ('number', 'supplier_invoice', 'supplier__name')
    ordering = ('-date_joined', '-id')


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'organization', 'cli', 'date_joined', 'status', 'document_type', 'total', 'balance', 'profit')
    list_filter = ('organization', 'status', 'document_type', 'payment_term')
    search_fields = ('id', 'number', 'cli__names', 'cli__surnames')
    ordering = ('-date_joined', '-id')


@admin.register(SalePayment)
class SalePaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'organization', 'sale', 'method', 'amount', 'paid_at')
    list_filter = ('organization', 'method')
    search_fields = ('reference', 'notes')
    ordering = ('-paid_at', '-id')


@admin.register(PurchasePayment)
class PurchasePaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'organization', 'purchase', 'method', 'amount', 'paid_at')
    list_filter = ('organization', 'method')
    search_fields = ('reference', 'notes')
    ordering = ('-paid_at', '-id')
