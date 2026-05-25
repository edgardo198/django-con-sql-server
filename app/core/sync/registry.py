from django.apps import apps


SYNC_MODEL_LABELS = [
    'user.storedmediafile',
    'user.organization',
    'user.user',
    'erp.category',
    'erp.supplier',
    'erp.client',
    'erp.taxrate',
    'erp.product',
    'erp.fiscaldata',
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

PARENT_UPDATED_FIELDS = {
    'erp.detpurchase': ('purchase', 'date_updated'),
    'erp.detsale': ('sale', 'date_updated'),
}


def get_model_label(model):
    return model._meta.label_lower


def get_sync_models():
    return [apps.get_model(label) for label in SYNC_MODEL_LABELS]


def get_sync_model(label):
    normalized_label = label.lower()
    if normalized_label not in SYNC_MODEL_LABELS:
        return None
    return apps.get_model(normalized_label)


def is_sync_model(model):
    return get_model_label(model) in SYNC_MODEL_LABELS
