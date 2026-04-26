from django.urls import path
from app.core.user.views import *

app_name = 'user'

urlpatterns = [
    path('organization/list/', OrganizationListView.as_view(), name='organization_list'),
    path('organization/add/', OrganizationCreateView.as_view(), name='organization_create'),
    path('organization/update/<int:pk>/', OrganizationUpdateView.as_view(), name='organization_update'),
    path('organization/delete/<int:pk>/', OrganizationDeleteView.as_view(), name='organization_delete'),
    path('organization/switch/<int:pk>/', SwitchOrganizationView.as_view(), name='organization_switch'),
    path('menu-layout/toggle/', MenuLayoutToggleView.as_view(), name='menu_layout_toggle'),
    # user
    path('list/', UserListView.as_view(), name='user_list'),
    path('add/', UserCreateView.as_view(), name='user_create'),
    path('update/<int:pk>/', UserUpdateView.as_view(), name='user_update'),
    path('delete/<int:pk>/', UserDeleteView.as_view(), name='user_delete'),
]
