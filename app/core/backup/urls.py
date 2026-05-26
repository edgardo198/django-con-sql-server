from django.urls import path

from app.core.backup.views import LocalBackupDownloadView, LocalBackupView


app_name = 'backup'

urlpatterns = [
    path('local/', LocalBackupView.as_view(), name='local'),
    path('local/download/<path:filename>/', LocalBackupDownloadView.as_view(), name='download'),
]
