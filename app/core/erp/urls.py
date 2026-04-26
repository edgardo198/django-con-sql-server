from django.urls import path

from app.core.erp.views.cashmovement.views import CashMovementCreateView, CashMovementDeleteView, CashMovementListView
from app.core.erp.views.cashsession.views import CashSessionCloseView, CashSessionCreateView, CashSessionListView
from app.core.erp.views.category.views import CategoryCreateView, CategoryDeleteView, CategoryListView, CategoryUpdateView
from app.core.erp.views.client.views import ClientCreateView, ClientDeleteView, ClientListView, ClientUpdateView
from app.core.erp.views.dashboard.views import DashboardView
from app.core.erp.views.fiscaldata.views import FiscalDataCreateView, FiscalDataManageView, FiscalDataUpdateView
from app.core.erp.views.inventorymovement.views import InventoryMovementListView
from app.core.erp.views.product.views import ProductCreateView, ProductDeleteView, ProductListView, ProductUpdateView
from app.core.erp.views.purchase.views import (
    PurchaseCancelView,
    PurchaseConfirmView,
    PurchaseCreateView,
    PurchaseDeleteView,
    PurchaseListView,
    PurchaseUpdateView,
)
from app.core.erp.views.sale.views import (
    SaleCancelView,
    SaleConfirmView,
    SaleCreateView,
    SaleDeleteView,
    SaleInvoicePdfView,
    SaleListView,
    SaleTicketPrintView,
    SaleUpdateView,
)
from app.core.erp.views.supplier.views import SupplierCreateView, SupplierDeleteView, SupplierListView, SupplierUpdateView
from app.core.erp.views.taxrate.views import TaxRateCreateView, TaxRateDeleteView, TaxRateListView, TaxRateUpdateView


app_name = 'erp'

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),

    path('category/list/', CategoryListView.as_view(), name='category_list'),
    path('category/add/', CategoryCreateView.as_view(), name='category_create'),
    path('category/update/<int:pk>/', CategoryUpdateView.as_view(), name='category_update'),
    path('category/delete/<int:pk>/', CategoryDeleteView.as_view(), name='category_delete'),

    path('client/list/', ClientListView.as_view(), name='client_list'),
    path('client/add/', ClientCreateView.as_view(), name='client_create'),
    path('client/update/<int:pk>/', ClientUpdateView.as_view(), name='client_update'),
    path('client/delete/<int:pk>/', ClientDeleteView.as_view(), name='client_delete'),

    path('product/list/', ProductListView.as_view(), name='product_list'),
    path('product/add/', ProductCreateView.as_view(), name='product_create'),
    path('product/update/<int:pk>/', ProductUpdateView.as_view(), name='product_update'),
    path('product/delete/<int:pk>/', ProductDeleteView.as_view(), name='product_delete'),

    path('supplier/list/', SupplierListView.as_view(), name='supplier_list'),
    path('supplier/add/', SupplierCreateView.as_view(), name='supplier_create'),
    path('supplier/update/<int:pk>/', SupplierUpdateView.as_view(), name='supplier_update'),
    path('supplier/delete/<int:pk>/', SupplierDeleteView.as_view(), name='supplier_delete'),

    path('tax-rate/list/', TaxRateListView.as_view(), name='taxrate_list'),
    path('tax-rate/add/', TaxRateCreateView.as_view(), name='taxrate_create'),
    path('tax-rate/update/<int:pk>/', TaxRateUpdateView.as_view(), name='taxrate_update'),
    path('tax-rate/delete/<int:pk>/', TaxRateDeleteView.as_view(), name='taxrate_delete'),

    path('fiscal-data/', FiscalDataManageView.as_view(), name='fiscaldata_manage'),
    path('fiscal-data/add/', FiscalDataCreateView.as_view(), name='fiscaldata_create'),
    path('fiscal-data/update/<int:pk>/', FiscalDataUpdateView.as_view(), name='fiscaldata_update'),

    path('cash-session/list/', CashSessionListView.as_view(), name='cashsession_list'),
    path('cash-session/add/', CashSessionCreateView.as_view(), name='cashsession_create'),
    path('cash-session/close/<int:pk>/', CashSessionCloseView.as_view(), name='cashsession_close'),

    path('cash-movement/list/', CashMovementListView.as_view(), name='cashmovement_list'),
    path('cash-movement/add/', CashMovementCreateView.as_view(), name='cashmovement_create'),
    path('cash-movement/delete/<int:pk>/', CashMovementDeleteView.as_view(), name='cashmovement_delete'),

    path('inventory-movement/list/', InventoryMovementListView.as_view(), name='inventorymovement_list'),

    path('purchase/list/', PurchaseListView.as_view(), name='purchase_list'),
    path('purchase/add/', PurchaseCreateView.as_view(), name='purchase_create'),
    path('purchase/update/<int:pk>/', PurchaseUpdateView.as_view(), name='purchase_update'),
    path('purchase/delete/<int:pk>/', PurchaseDeleteView.as_view(), name='purchase_delete'),
    path('purchase/confirm/<int:pk>/', PurchaseConfirmView.as_view(), name='purchase_confirm'),
    path('purchase/cancel/<int:pk>/', PurchaseCancelView.as_view(), name='purchase_cancel'),

    path('sale/list/', SaleListView.as_view(), name='sale_list'),
    path('sale/add/', SaleCreateView.as_view(), name='sale_create'),
    path('sale/update/<int:pk>/', SaleUpdateView.as_view(), name='sale_update'),
    path('sale/delete/<int:pk>/', SaleDeleteView.as_view(), name='sale_delete'),
    path('sale/confirm/<int:pk>/', SaleConfirmView.as_view(), name='sale_confirm'),
    path('sale/cancel/<int:pk>/', SaleCancelView.as_view(), name='sale_cancel'),
    path('sale/invoice/pdf/<int:pk>/', SaleInvoicePdfView.as_view(), name='sale_invoice_pdf'),
    path('sale/ticket/print/<int:pk>/', SaleTicketPrintView.as_view(), name='sale_ticket_print'),
]
