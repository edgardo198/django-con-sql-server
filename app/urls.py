"""app URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from .core.homepage.views import IndexView
from .core.erp.views.supplier.views import SupplierCreateView, SupplierDeleteView, SupplierListView, SupplierUpdateView
from .core.user.views import OrganizationListView, SwitchOrganizationView

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', include('app.core.login.urls')),
    # Compatibilidad con codigo legado que usa reverse('supplier_list')
    # en lugar de reverse('erp:supplier_list').
    path('erp/supplier/list/', SupplierListView.as_view(), name='supplier_list'),
    path('erp/supplier/add/', SupplierCreateView.as_view(), name='supplier_create'),
    path('erp/supplier/update/<int:pk>/', SupplierUpdateView.as_view(), name='supplier_update'),
    path('erp/supplier/delete/<int:pk>/', SupplierDeleteView.as_view(), name='supplier_delete'),
    path('erp/', include(('app.core.erp.urls', 'erp'), namespace='erp')),
    path('report/', include('app.core.reports.urls')),
    path('user/', include(('app.core.user.urls', 'user'), namespace='user')),
    path('user/organization/list/', OrganizationListView.as_view(), name='organization_list'),
    path('user/organization/switch/<int:pk>/', SwitchOrganizationView.as_view(), name='organization_switch'),
    path('', IndexView.as_view(), name='index'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)





