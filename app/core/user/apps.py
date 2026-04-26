from django.apps import AppConfig


class UserConfig(AppConfig):
    name = 'app.core.user'

    def ready(self):
        import app.core.user.signals  # noqa: F401
