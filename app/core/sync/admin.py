from django.contrib import admin

from app.core.sync.models import (
    SyncConfiguration,
    SyncConflict,
    SyncIdentity,
    SyncOutbox,
    SyncRunLock,
    SyncState,
    SyncTombstone,
)


@admin.register(SyncIdentity)
class SyncIdentityAdmin(admin.ModelAdmin):
    list_display = ('model_label', 'object_id', 'sync_uuid', 'updated_at')
    search_fields = ('model_label', 'sync_uuid')
    list_filter = ('model_label',)


@admin.register(SyncOutbox)
class SyncOutboxAdmin(admin.ModelAdmin):
    list_display = ('model_label', 'sync_uuid', 'action', 'processed_at', 'attempt_count', 'created_at')
    search_fields = ('model_label', 'sync_uuid', 'error')
    list_filter = ('model_label', 'action', 'processed_at')
    readonly_fields = ('created_at', 'last_attempt_at', 'processed_at')


@admin.register(SyncTombstone)
class SyncTombstoneAdmin(admin.ModelAdmin):
    list_display = ('model_label', 'sync_uuid', 'deleted_at')
    search_fields = ('model_label', 'sync_uuid')
    list_filter = ('model_label',)


@admin.register(SyncState)
class SyncStateAdmin(admin.ModelAdmin):
    list_display = ('remote_url', 'last_pull_at', 'last_push_at', 'updated_at')
    search_fields = ('remote_url', 'last_error')
    readonly_fields = ('updated_at',)


@admin.register(SyncConfiguration)
class SyncConfigurationAdmin(admin.ModelAdmin):
    list_display = ('key', 'remote_sync_enabled', 'remote_url', 'updated_by', 'updated_at')
    readonly_fields = ('updated_at',)


@admin.register(SyncRunLock)
class SyncRunLockAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'locked_until', 'updated_at')
    search_fields = ('name', 'owner')


@admin.register(SyncConflict)
class SyncConflictAdmin(admin.ModelAdmin):
    list_display = ('model_label', 'sync_uuid', 'resolved', 'created_at')
    search_fields = ('model_label', 'sync_uuid', 'description')
    list_filter = ('model_label', 'resolved')
