import os

from app.core.sync.models import SyncConfiguration


FALSE_VALUES = {'0', 'false', 'no', 'off'}


def env_flag(name, default=True):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in FALSE_VALUES


def default_remote_sync_enabled():
    return env_flag('CLOUD_BACKUP_ENABLED', default=True)


def get_sync_configuration():
    configuration, _ = SyncConfiguration.objects.get_or_create(
        key=SyncConfiguration.DEFAULT_KEY,
        defaults={'remote_sync_enabled': default_remote_sync_enabled()},
    )
    return configuration


def env_sync_remote_url():
    return (os.getenv('SYNC_REMOTE_URL') or '').strip()


def env_sync_token():
    return (os.getenv('SYNC_API_TOKEN') or os.getenv('DJANGO_SYNC_TOKEN') or '').strip()


def get_configured_remote_url():
    configuration = get_sync_configuration()
    return (configuration.remote_url or env_sync_remote_url()).strip()


def get_configured_sync_token():
    configuration = get_sync_configuration()
    return (configuration.sync_token or env_sync_token()).strip()


def update_sync_connection(remote_url, sync_token='', user=None):
    configuration = get_sync_configuration()
    configuration.remote_url = (remote_url or '').strip().rstrip('/')
    if sync_token:
        configuration.sync_token = sync_token.strip()
    if user and user.is_authenticated:
        configuration.updated_by = user
    configuration.save(update_fields=['remote_url', 'sync_token', 'updated_by', 'updated_at'])
    return configuration


def is_remote_sync_enabled():
    return get_sync_configuration().remote_sync_enabled


def set_remote_sync_enabled(enabled, user=None):
    configuration = get_sync_configuration()
    configuration.remote_sync_enabled = bool(enabled)
    if user and user.is_authenticated:
        configuration.updated_by = user
    configuration.save(update_fields=['remote_sync_enabled', 'updated_by', 'updated_at'])
    return configuration
