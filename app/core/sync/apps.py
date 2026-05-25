from django.apps import AppConfig


class SyncConfig(AppConfig):
    name = 'app.core.sync'
    verbose_name = 'Sincronizacion'

    def ready(self):
        from app.core.sync import signals  # noqa: F401
