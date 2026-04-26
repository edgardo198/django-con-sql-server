from django.db.utils import OperationalError, ProgrammingError
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from app.core.user.access import ensure_role_groups, sync_super_admin_group_membership


@receiver(post_migrate)
def create_default_access_roles(sender, **kwargs):
    try:
        ensure_role_groups()
        sync_super_admin_group_membership()
    except (OperationalError, ProgrammingError):
        return
