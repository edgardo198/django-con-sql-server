from django.core.management.base import BaseCommand

from app.core.sync.models import SyncOutbox
from app.core.sync.registry import get_outgoing_model_labels_for_current_node
from app.core.sync.services import is_remote_sync_enabled


class Command(BaseCommand):
    help = 'Devuelve la cantidad de cambios locales pendientes de sincronizar.'

    def handle(self, *args, **options):
        if not is_remote_sync_enabled():
            self.stdout.write('0')
            return

        count = SyncOutbox.objects.filter(
            processed_at__isnull=True,
            model_label__in=get_outgoing_model_labels_for_current_node(),
        ).count()
        self.stdout.write(str(count))
