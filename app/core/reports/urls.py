from django.urls import path
from app.core.reports.views import ReportSaleView

urlpatterns = [
    path('sale/', ReportSaleView.as_view(), name='sale_report')
]

