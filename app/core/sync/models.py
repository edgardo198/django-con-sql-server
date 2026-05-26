import uuid

from django.db import models
from django.utils import timezone


class SyncIdentity(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    model_label = models.CharField(max_length=100, db_index=True)
    object_id = models.BigIntegerField(db_index=True)
    sync_uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (('model_label', 'object_id'),)
        ordering = ['model_label', 'object_id']

    def __str__(self):
        return '{}:{} -> {}'.format(self.model_label, self.object_id, self.sync_uuid)


class SyncOutbox(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    ACTION_UPSERT = 'upsert'
    ACTION_DELETE = 'delete'
    ACTION_CHOICES = (
        (ACTION_UPSERT, 'Crear/actualizar'),
        (ACTION_DELETE, 'Eliminar'),
    )

    model_label = models.CharField(max_length=100, db_index=True)
    object_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    sync_uuid = models.UUIDField(db_index=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    attempt_count = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return '{} {} {}'.format(self.action, self.model_label, self.sync_uuid)


class SyncTombstone(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    model_label = models.CharField(max_length=100, db_index=True)
    sync_uuid = models.UUIDField(db_index=True)
    deleted_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        unique_together = (('model_label', 'sync_uuid'),)
        ordering = ['deleted_at']

    def __str__(self):
        return 'delete {} {}'.format(self.model_label, self.sync_uuid)


class SyncState(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    remote_url = models.URLField(unique=True)
    last_pull_at = models.DateTimeField(null=True, blank=True)
    last_push_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['remote_url']

    def __str__(self):
        return self.remote_url


class SyncConfiguration(models.Model):
    DEFAULT_KEY = 'default'

    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    key = models.CharField(max_length=40, unique=True, default=DEFAULT_KEY)
    remote_sync_enabled = models.BooleanField(default=True)
    remote_url = models.URLField(blank=True)
    sync_token = models.CharField(max_length=255, blank=True)
    updated_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sync_configuration_updates',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuracion de sincronizacion'
        verbose_name_plural = 'Configuraciones de sincronizacion'

    def __str__(self):
        return 'Sincronizacion remota {}'.format('activa' if self.remote_sync_enabled else 'pausada')


class SyncRunLock(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    name = models.CharField(max_length=80, unique=True)
    owner = models.CharField(max_length=100, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class SyncConflict(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    model_label = models.CharField(max_length=100, db_index=True)
    sync_uuid = models.UUIDField(db_index=True)
    local_updated_at = models.DateTimeField(null=True, blank=True)
    remote_updated_at = models.DateTimeField(null=True, blank=True)
    description = models.TextField()
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return '{} {}'.format(self.model_label, self.sync_uuid)
