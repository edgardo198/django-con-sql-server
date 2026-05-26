import os

from django.apps import apps


CENTRAL_TO_LOCAL_MODEL_LABELS = [
    'user.storedmediafile',
    'user.organization',
    'user.user',
    'erp.category',
    'erp.supplier',
    'erp.taxrate',
    'erp.product',
    'erp.fiscaldata',
]

LOCAL_TO_CENTRAL_MODEL_LABELS = [
    'erp.cashsession',
    'erp.cashmovement',
    'erp.inventorymovement',
    'erp.purchase',
    'erp.detpurchase',
    'erp.sale',
    'erp.detsale',
    'erp.salepayment',
    'erp.purchasepayment',
]

BIDIRECTIONAL_MODEL_LABELS = [
    'erp.client',
]

SYNC_MODEL_LABELS = list(dict.fromkeys(
    CENTRAL_TO_LOCAL_MODEL_LABELS
    + LOCAL_TO_CENTRAL_MODEL_LABELS
    + BIDIRECTIONAL_MODEL_LABELS
))

NODE_ROLE_LOCAL = 'local'
NODE_ROLE_CENTRAL = 'central'
NODE_ROLE_ALIASES = {
    'cloud': NODE_ROLE_CENTRAL,
    'render': NODE_ROLE_CENTRAL,
    'server': NODE_ROLE_CENTRAL,
    'central': NODE_ROLE_CENTRAL,
    'local': NODE_ROLE_LOCAL,
    'pos': NODE_ROLE_LOCAL,
    'caja': NODE_ROLE_LOCAL,
    'store': NODE_ROLE_LOCAL,
}

SYNC_MODEL_GROUPS = [
    {
        'title': 'Render baja a cajas',
        'description': 'Productos, precios, usuarios y configuracion central.',
        'labels': CENTRAL_TO_LOCAL_MODEL_LABELS,
    },
    {
        'title': 'Cajas suben a Render',
        'description': 'Ventas, compras, pagos, cierres y movimientos locales.',
        'labels': LOCAL_TO_CENTRAL_MODEL_LABELS,
    },
    {
        'title': 'Ambos sentidos',
        'description': 'Clientes creados o actualizados en cualquier lado.',
        'labels': BIDIRECTIONAL_MODEL_LABELS,
    },
]

PARENT_UPDATED_FIELDS = {
    'erp.detpurchase': ('purchase', 'date_updated'),
    'erp.detsale': ('sale', 'date_updated'),
}


def get_sync_node_role():
    role = (os.getenv('SYNC_NODE_ROLE') or '').strip().lower()
    if not role:
        role = NODE_ROLE_CENTRAL if os.getenv('RENDER') else NODE_ROLE_LOCAL
    return NODE_ROLE_ALIASES.get(role, role)


def is_central_node():
    return get_sync_node_role() == NODE_ROLE_CENTRAL


def get_outgoing_model_labels_for_current_node():
    if is_central_node():
        labels = CENTRAL_TO_LOCAL_MODEL_LABELS + BIDIRECTIONAL_MODEL_LABELS
    else:
        labels = LOCAL_TO_CENTRAL_MODEL_LABELS + BIDIRECTIONAL_MODEL_LABELS
    return list(dict.fromkeys(labels))


def get_incoming_model_labels_for_current_node():
    if is_central_node():
        labels = LOCAL_TO_CENTRAL_MODEL_LABELS + BIDIRECTIONAL_MODEL_LABELS
    else:
        labels = CENTRAL_TO_LOCAL_MODEL_LABELS + BIDIRECTIONAL_MODEL_LABELS
    return list(dict.fromkeys(labels))


def is_outgoing_model_label(model_label):
    return model_label.lower() in get_outgoing_model_labels_for_current_node()


def is_incoming_model_label(model_label):
    return model_label.lower() in get_incoming_model_labels_for_current_node()


def get_model_label(model):
    return model._meta.label_lower


def get_sync_models():
    return [apps.get_model(label) for label in SYNC_MODEL_LABELS]


def get_sync_models_for_labels(labels):
    return [apps.get_model(label) for label in labels if label in SYNC_MODEL_LABELS]


def get_sync_model(label):
    normalized_label = label.lower()
    if normalized_label not in SYNC_MODEL_LABELS:
        return None
    return apps.get_model(normalized_label)


def is_sync_model(model):
    return get_model_label(model) in SYNC_MODEL_LABELS
