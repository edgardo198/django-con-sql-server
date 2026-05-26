from django.urls import path

from app.core.sync import views


app_name = 'sync'

urlpatterns = [
    path('panel/', views.SyncStatusPanelView.as_view(), name='panel'),
    path('status/', views.sync_status, name='status'),
    path('pull/', views.sync_pull, name='pull'),
    path('push/', views.sync_push, name='push'),
]
