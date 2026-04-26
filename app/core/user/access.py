from collections import OrderedDict

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


ROLE_SUPER_ADMIN = 'Super Admin'
ROLE_STORE_ADMIN = 'Admin de Tienda'
ROLE_SUBMANAGER = 'Subgerente'
ROLE_SELLER = 'Vendedor'

ROLE_PRIORITY = {
    ROLE_SUPER_ADMIN: 100,
    ROLE_STORE_ADMIN: 80,
    ROLE_SUBMANAGER: 50,
    ROLE_SELLER: 10,
}

ROLE_PERMISSIONS = OrderedDict({
    ROLE_SUPER_ADMIN: {
        'user.organization': ('add', 'change', 'delete', 'view'),
        'user.user': ('add', 'change', 'delete', 'view'),
        'erp.category': ('add', 'change', 'delete', 'view'),
        'erp.product': ('add', 'change', 'delete', 'view'),
        'erp.client': ('add', 'change', 'delete', 'view'),
        'erp.supplier': ('add', 'change', 'delete', 'view'),
        'erp.taxrate': ('add', 'change', 'delete', 'view'),
        'erp.fiscaldata': ('add', 'change', 'delete', 'view'),
        'erp.cashsession': ('add', 'change', 'delete', 'view'),
        'erp.cashmovement': ('add', 'change', 'delete', 'view'),
        'erp.inventorymovement': ('add', 'change', 'delete', 'view'),
        'erp.purchase': ('add', 'change', 'delete', 'view'),
        'erp.purchasepayment': ('add', 'change', 'delete', 'view'),
        'erp.sale': ('add', 'change', 'delete', 'view'),
        'erp.salepayment': ('add', 'change', 'delete', 'view'),
    },
    ROLE_STORE_ADMIN: {
        'user.organization': ('view', 'change'),
        'user.user': ('add', 'change', 'view'),
        'erp.category': ('add', 'change', 'delete', 'view'),
        'erp.product': ('add', 'change', 'delete', 'view'),
        'erp.client': ('add', 'change', 'delete', 'view'),
        'erp.supplier': ('add', 'change', 'delete', 'view'),
        'erp.taxrate': ('add', 'change', 'delete', 'view'),
        'erp.fiscaldata': ('add', 'change', 'view'),
        'erp.cashsession': ('add', 'change', 'view'),
        'erp.cashmovement': ('add', 'delete', 'view'),
        'erp.inventorymovement': ('view',),
        'erp.purchase': ('add', 'change', 'delete', 'view'),
        'erp.purchasepayment': ('add', 'change', 'delete', 'view'),
        'erp.sale': ('add', 'change', 'delete', 'view'),
        'erp.salepayment': ('add', 'change', 'delete', 'view'),
    },
    ROLE_SUBMANAGER: {
        'user.organization': ('view',),
        'erp.category': ('add', 'change', 'view'),
        'erp.product': ('add', 'change', 'view'),
        'erp.client': ('add', 'change', 'view'),
        'erp.supplier': ('add', 'change', 'view'),
        'erp.taxrate': ('view',),
        'erp.cashsession': ('add', 'change', 'view'),
        'erp.cashmovement': ('add', 'view'),
        'erp.inventorymovement': ('view',),
        'erp.purchase': ('add', 'change', 'view'),
        'erp.purchasepayment': ('add', 'view'),
        'erp.sale': ('add', 'change', 'view'),
        'erp.salepayment': ('add', 'view'),
    },
    ROLE_SELLER: {
        'erp.category': ('view',),
        'erp.product': ('view',),
        'erp.client': ('add', 'change', 'view'),
        'erp.cashsession': ('add', 'change', 'view'),
        'erp.cashmovement': ('add', 'view'),
        'erp.inventorymovement': ('view',),
        'erp.sale': ('add', 'change', 'view'),
        'erp.salepayment': ('add', 'view'),
    },
})


def get_role_names():
    return list(ROLE_PERMISSIONS.keys())


def get_role_priority(role_name):
    return ROLE_PRIORITY.get(role_name, 0)


def get_highest_role_priority(role_names):
    return max((get_role_priority(role_name) for role_name in role_names), default=0)


def sort_role_names(role_names):
    return sorted(
        set(role_names),
        key=get_role_priority,
        reverse=True,
    )


def get_role_permissions_map():
    return ROLE_PERMISSIONS


def build_permission_codenames(actions, model_name):
    return ['{}_{}'.format(action, model_name) for action in actions]


def get_permissions_for_model(app_label, model_name, actions):
    try:
        content_type = ContentType.objects.get(app_label=app_label, model=model_name)
    except ContentType.DoesNotExist:
        return Permission.objects.none()
    codenames = build_permission_codenames(actions, model_name)
    return Permission.objects.filter(content_type=content_type, codename__in=codenames)


def ensure_role_groups():
    groups = {}
    for role_name, permission_map in get_role_permissions_map().items():
        group, _ = Group.objects.get_or_create(name=role_name)
        permissions = Permission.objects.none()

        for model_key, actions in permission_map.items():
            app_label, model_name = model_key.split('.', 1)
            permissions = permissions | get_permissions_for_model(app_label, model_name, actions)

        group.permissions.set(permissions.distinct())
        groups[role_name] = group

    return groups


def sync_super_admin_group_membership():
    groups = ensure_role_groups()
    super_admin_group = groups[ROLE_SUPER_ADMIN]
    user_model = get_user_model()
    for user in user_model.objects.filter(is_superuser=True):
        user.groups.add(super_admin_group)


def get_user_role_priority(user):
    if getattr(user, 'is_superuser', False):
        return get_role_priority(ROLE_SUPER_ADMIN)

    if hasattr(user, 'get_role_names'):
        return get_highest_role_priority(user.get_role_names())

    if hasattr(user, 'groups'):
        return get_highest_role_priority(user.groups.values_list('name', flat=True))

    return 0


def can_manage_user(manager, target):
    if not getattr(manager, 'is_authenticated', False) or target is None:
        return False

    if getattr(manager, 'is_superuser', False):
        return True

    if getattr(target, 'is_superuser', False):
        return False

    if manager.pk == target.pk:
        if hasattr(manager, 'can_manage_users'):
            return manager.can_manage_users()
        return bool(get_assignable_role_names(manager))

    if not hasattr(manager, 'get_manageable_organizations') or not hasattr(target, 'organizations'):
        return False

    manager_organization_ids = set(manager.get_manageable_organizations().values_list('pk', flat=True))
    target_organization_ids = set(target.organizations.values_list('pk', flat=True))
    if not manager_organization_ids.intersection(target_organization_ids):
        return False

    return get_user_role_priority(manager) > get_user_role_priority(target)


def get_assignable_role_names(user):
    if getattr(user, 'is_superuser', False):
        return get_role_names()

    user_role_names = set(user.groups.values_list('name', flat=True))
    if ROLE_STORE_ADMIN in user_role_names:
        return [ROLE_SUBMANAGER, ROLE_SELLER]

    return []
