from django.apps import AppConfig


class BackupConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app.core.backup'
    verbose_name = 'Respaldos locales'
