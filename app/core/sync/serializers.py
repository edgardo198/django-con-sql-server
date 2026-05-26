import uuid
import base64
from collections import OrderedDict
from decimal import Decimal

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.base import File
from django.db import models
from django.db.models import F
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime, parse_time

from app.core.sync.context import suppress_sync_outbox
from app.core.sync.models import SyncConflict, SyncIdentity, SyncOutbox, SyncTombstone
from app.core.sync.registry import (
    PARENT_UPDATED_FIELDS,
    get_model_label,
    get_outgoing_model_labels_for_current_node,
    get_sync_model,
    get_sync_models_for_labels,
    is_incoming_model_label,
    is_sync_model,
)


def get_identity_for_instance(instance):
    identity, _ = SyncIdentity.objects.get_or_create(
        model_label=get_model_label(type(instance)),
        object_id=instance.pk,
    )
    return identity


def get_object_for_identity(model_label, sync_uuid):
    identity = SyncIdentity.objects.filter(
        model_label=model_label,
        sync_uuid=sync_uuid,
    ).first()
    if not identity:
        return None
    model = get_sync_model(model_label)
    if model is None:
        return None
    return model.objects.filter(pk=identity.object_id).first()


def normalize_datetime(value):
    if not value:
        return None
    if isinstance(value, str):
        value = parse_datetime(value)
    if value and timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return value


def primitive_value(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {
            'encoding': 'base64',
            'data': base64.b64encode(bytes(value)).decode('ascii'),
        }
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    if isinstance(value, File):
        return value.name
    return value


def field_value(instance, field):
    if isinstance(field, models.BinaryField):
        return primitive_value(getattr(instance, field.name))

    if isinstance(field, models.ForeignKey):
        related_pk = getattr(instance, '{}_id'.format(field.name), None)
        if related_pk is None:
            return None
        related_model = field.remote_field.model
        if is_sync_model(related_model):
            related = getattr(instance, field.name, None)
            if related is None:
                related = related_model.objects.filter(pk=related_pk).first()
            if related is None:
                return None
            return str(get_identity_for_instance(related).sync_uuid)
        return related_pk

    value = getattr(instance, field.name)
    if isinstance(field, models.FileField):
        return value.name if value else ''
    return primitive_value(value)


def get_updated_at(instance):
    for field_name in ('date_updated', 'updated_at', 'modified_at'):
        if hasattr(instance, field_name):
            value = getattr(instance, field_name)
            if value:
                return value
    if hasattr(instance, 'date_joined'):
        return instance.date_joined
    if hasattr(instance, 'date_creation'):
        return instance.date_creation
    return timezone.now()


def serialize_instance(instance):
    model = type(instance)
    fields = {}

    for field in model._meta.fields:
        if field.primary_key or field.name == 'id':
            continue
        fields[field.name] = field_value(instance, field)

    m2m = {}
    user_model = get_user_model()
    if isinstance(instance, user_model):
        m2m['groups'] = list(instance.groups.values_list('name', flat=True))
        m2m['organizations'] = [
            str(get_identity_for_instance(organization).sync_uuid)
            for organization in instance.organizations.all()
        ]

    identity = get_identity_for_instance(instance)
    return {
        'model': get_model_label(model),
        'sync_uuid': str(identity.sync_uuid),
        'deleted': False,
        'updated_at': primitive_value(get_updated_at(instance)),
        'fields': fields,
        'm2m': m2m,
    }


def serialize_tombstone(tombstone):
    return {
        'model': tombstone.model_label,
        'sync_uuid': str(tombstone.sync_uuid),
        'deleted': True,
        'updated_at': primitive_value(tombstone.deleted_at),
        'fields': {},
        'm2m': {},
    }


def parse_field_value(field, value):
    if value is None:
        return None
    if isinstance(field, models.DateTimeField):
        return normalize_datetime(value)
    if isinstance(field, models.DateField):
        return parse_date(value) if isinstance(value, str) else value
    if isinstance(field, models.TimeField):
        return parse_time(value) if isinstance(value, str) else value
    if isinstance(field, models.DecimalField):
        return Decimal(str(value or 0))
    if isinstance(field, models.BooleanField):
        return bool(value)
    if isinstance(field, models.IntegerField):
        return int(value)
    if isinstance(field, models.UUIDField):
        return uuid.UUID(str(value))
    if isinstance(field, models.BinaryField):
        if value in (None, ''):
            return b''
        if isinstance(value, dict) and value.get('encoding') == 'base64':
            return base64.b64decode(value.get('data') or '')
        if isinstance(value, str):
            return base64.b64decode(value)
        return bytes(value)
    return value


def resolve_fk(field, value):
    if value in (None, ''):
        return None, True
    related_model = field.remote_field.model
    if not is_sync_model(related_model):
        return value, True
    related_label = get_model_label(related_model)
    related = get_object_for_identity(related_label, value)
    if related is None:
        return None, field.null or field.blank
    return related.pk, True


def find_existing_instance(model, fields, fk_values):
    user_model = get_user_model()
    if model is user_model and fields.get('username'):
        return model.objects.filter(username=fields['username']).first()

    model_label = get_model_label(model)
    organization_id = fk_values.get('organization')

    if model_label == 'user.organization':
        code = fields.get('code')
        if code:
            found = model.objects.filter(code=code).first()
            if found:
                return found
        name = fields.get('name')
        if name:
            return model.objects.filter(name=name).first()

    if model_label == 'user.storedmediafile' and fields.get('name'):
        return model.objects.filter(name=fields['name']).first()

    if model_label in ('erp.category', 'erp.supplier') and organization_id and fields.get('name'):
        return model.objects.filter(organization_id=organization_id, name=fields['name']).first()

    if model_label == 'erp.taxrate' and organization_id and fields.get('code'):
        return model.objects.filter(organization_id=organization_id, code=fields['code']).first()

    if model_label == 'erp.client' and organization_id:
        for field_name in ('dni', 'rtn'):
            value = fields.get(field_name)
            if value:
                found = model.objects.filter(organization_id=organization_id, **{field_name: value}).first()
                if found:
                    return found

    if model_label == 'erp.product' and organization_id:
        for field_name in ('barcode', 'internal_code', 'name'):
            value = fields.get(field_name)
            if value:
                found = model.objects.filter(organization_id=organization_id, **{field_name: value}).first()
                if found:
                    return found

    if model_label == 'erp.fiscaldata' and organization_id:
        return model.objects.filter(organization_id=organization_id).first()

    return None


def bind_identity(model_label, obj, sync_uuid):
    SyncIdentity.objects.update_or_create(
        model_label=model_label,
        object_id=obj.pk,
        defaults={'sync_uuid': sync_uuid},
    )


def save_imported_instance(obj):
    models.Model.save(obj)


def delete_imported_instance(obj):
    models.Model.delete(obj)


def apply_user_m2m(obj, m2m):
    if not m2m:
        return

    group_names = m2m.get('groups')
    if group_names is not None:
        groups = []
        for group_name in group_names:
            group, _ = Group.objects.get_or_create(name=group_name)
            groups.append(group)
        obj.groups.set(groups)

    organization_uuids = m2m.get('organizations')
    if organization_uuids is not None:
        Organization = apps.get_model('user.organization')
        organizations = []
        for organization_uuid in organization_uuids:
            organization = get_object_for_identity(get_model_label(Organization), organization_uuid)
            if organization:
                organizations.append(organization)
        obj.organizations.set(organizations)


def apply_record(record):
    model_label = (record.get('model') or '').lower()
    if not is_incoming_model_label(model_label):
        return {'status': 'ignored', 'reason': 'Modelo no permitido para este nodo: {}'.format(model_label)}

    model = get_sync_model(model_label)
    if model is None:
        return {'status': 'ignored', 'reason': 'Modelo no sincronizable: {}'.format(model_label)}

    sync_uuid = uuid.UUID(str(record['sync_uuid']))
    updated_at = normalize_datetime(record.get('updated_at')) or timezone.now()

    if record.get('deleted'):
        obj = get_object_for_identity(model_label, sync_uuid)
        with suppress_sync_outbox():
            if obj is not None:
                delete_imported_instance(obj)
            SyncTombstone.objects.update_or_create(
                model_label=model_label,
                sync_uuid=sync_uuid,
                defaults={'deleted_at': updated_at},
            )
        return {'status': 'deleted'}

    fields = record.get('fields') or {}
    fk_values = {}
    unresolved = []

    for field in model._meta.fields:
        if field.primary_key or field.name not in fields or not isinstance(field, models.ForeignKey):
            continue
        value, resolved = resolve_fk(field, fields[field.name])
        if not resolved:
            unresolved.append(field.name)
        fk_values[field.name] = value

    if unresolved:
        return {'status': 'deferred', 'reason': 'FK pendiente: {}'.format(', '.join(unresolved))}

    identity = SyncIdentity.objects.filter(model_label=model_label, sync_uuid=sync_uuid).first()
    obj = model.objects.filter(pk=identity.object_id).first() if identity else None
    if obj is None:
        obj = find_existing_instance(model, fields, fk_values) or model()

    local_updated_at = get_updated_at(obj) if obj.pk else None
    if model_label != 'user.user' and local_updated_at and updated_at and local_updated_at > updated_at:
        SyncConflict.objects.create(
            model_label=model_label,
            sync_uuid=sync_uuid,
            local_updated_at=local_updated_at,
            remote_updated_at=updated_at,
            description='Cambio remoto mas antiguo que el cambio local. Se conservo el dato local.',
        )
        bind_identity(model_label, obj, sync_uuid)
        return {'status': 'conflict'}

    with suppress_sync_outbox():
        for field in model._meta.fields:
            if field.primary_key or field.name == 'id' or field.name not in fields:
                continue
            if isinstance(field, models.ForeignKey):
                setattr(obj, '{}_id'.format(field.name), fk_values.get(field.name))
            elif isinstance(field, models.FileField):
                setattr(obj, field.name, fields[field.name] or '')
            else:
                setattr(obj, field.name, parse_field_value(field, fields[field.name]))

        save_imported_instance(obj)
        bind_identity(model_label, obj, sync_uuid)
        apply_user_m2m(obj, record.get('m2m') or {})

        update_fields = {}
        if hasattr(obj, 'date_updated'):
            update_fields['date_updated'] = updated_at
        if update_fields:
            model.objects.filter(pk=obj.pk).update(**update_fields)

    return {'status': 'applied'}


def apply_records(records, max_passes=4):
    pending = list(records)
    results = []

    for _ in range(max_passes):
        if not pending:
            break

        next_pending = []
        applied_this_pass = 0
        for record in pending:
            result = apply_record(record)
            if result.get('status') == 'deferred':
                next_pending.append(record)
                continue
            results.append(result)
            applied_this_pass += 1

        if len(next_pending) == len(pending) and applied_this_pass == 0:
            for record in next_pending:
                results.append({
                    'status': 'deferred',
                    'reason': 'Dependencias pendientes tras varios intentos.',
                    'model': record.get('model'),
                    'sync_uuid': record.get('sync_uuid'),
                })
            break

        pending = next_pending

    return results


def queryset_changed_since(model, since):
    queryset = model.objects.all()
    model_label = get_model_label(model)

    if since is None:
        return queryset

    if model_label == 'user.user':
        return queryset

    if hasattr(model, 'date_updated'):
        return queryset.filter(date_updated__gt=since)

    parent_info = PARENT_UPDATED_FIELDS.get(model_label)
    if parent_info:
        parent_field, updated_field = parent_info
        return queryset.filter(**{'{}__{}__gt'.format(parent_field, updated_field): since})

    return queryset


def collect_pull_records(since=None, offset=0, limit=None):
    records = []
    outgoing_labels = get_outgoing_model_labels_for_current_node()
    for model in get_sync_models_for_labels(outgoing_labels):
        for obj in queryset_changed_since(model, since).order_by('pk'):
            records.append(serialize_instance(obj))

    tombstones = SyncTombstone.objects.filter(model_label__in=outgoing_labels)
    if since is not None:
        tombstones = tombstones.filter(deleted_at__gt=since)
    for tombstone in tombstones.order_by('deleted_at', 'pk'):
        records.append(serialize_tombstone(tombstone))

    total = len(records)
    if limit is None:
        return records, total, False

    sliced_records = records[offset:offset + limit]
    has_more = offset + limit < total
    return sliced_records, total, has_more


def serialize_outbox_item(item):
    if item.action == SyncOutbox.ACTION_DELETE:
        tombstone = SyncTombstone.objects.filter(
            model_label=item.model_label,
            sync_uuid=item.sync_uuid,
        ).first()
        if tombstone:
            return serialize_tombstone(tombstone)
        return {
            'model': item.model_label,
            'sync_uuid': str(item.sync_uuid),
            'deleted': True,
            'updated_at': primitive_value(item.created_at),
            'fields': {},
            'm2m': {},
        }

    model = get_sync_model(item.model_label)
    if model is None or item.object_id is None:
        return None
    obj = model.objects.filter(pk=item.object_id).first()
    if obj is None:
        return {
            'model': item.model_label,
            'sync_uuid': str(item.sync_uuid),
            'deleted': True,
            'updated_at': primitive_value(item.created_at),
            'fields': {},
            'm2m': {},
        }
    return serialize_instance(obj)


def get_pending_outbox(limit=250):
    fetch_limit = max(limit * 5, limit)
    outgoing_labels = get_outgoing_model_labels_for_current_node()
    pending_items = list(
        SyncOutbox.objects
        .filter(processed_at__isnull=True, model_label__in=outgoing_labels)
        .order_by('created_at', 'id')[:fetch_limit]
    )

    grouped = OrderedDict()
    grouped_ids = {}
    for item in pending_items:
        key = (item.model_label, str(item.sync_uuid))
        grouped[key] = item
        grouped_ids.setdefault(key, []).append(item.id)

    selected = []
    for key, item in grouped.items():
        item._selected_outbox_ids = grouped_ids[key]
        selected.append(item)
        if len(selected) >= limit:
            break

    return selected


def mark_outbox_processed(items):
    item_ids = []
    for item in items:
        item_ids.extend(getattr(item, '_selected_outbox_ids', [item.id]))
    if item_ids:
        SyncOutbox.objects.filter(pk__in=item_ids).update(
            processed_at=timezone.now(),
            last_attempt_at=timezone.now(),
            error='',
        )


def mark_outbox_failed(items, error):
    item_ids = []
    for item in items:
        item_ids.extend(getattr(item, '_selected_outbox_ids', [item.id]))
    if item_ids:
        SyncOutbox.objects.filter(pk__in=item_ids).update(
            attempt_count=F('attempt_count') + 1,
            last_attempt_at=timezone.now(),
            error=str(error)[:2000],
        )
