from django.core.management.base import BaseCommand

from app.core.sync.models import SyncOutbox


class Command(BaseCommand):
    help = 'Devuelve la cantidad de cambios locales pendientes de sincronizar.'

    def handle(self, *args, **options):
        count = SyncOutbox.objects.filter(processed_at__isnull=True).count()
        self.stdout.write(str(count))
