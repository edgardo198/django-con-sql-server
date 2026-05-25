"""
Django settings for app project.
"""

import os

import app.core.db as db
from django.core.exceptions import ImproperlyConfigured


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=None):
    value = os.getenv(name)
    if value is None:
        return default or []
    return [item.strip() for item in value.split(',') if item.strip()]


def csrf_origin(value):
    if '://' in value:
        return value
    return 'https://{}'.format(value)


def url_path(value, default='/'):
    value = (value or default).strip()
    if '://' in value:
        from urllib.parse import urlparse

        value = urlparse(value).path or default
    if not value.startswith('/'):
        value = '/{}'.format(value)
    if not value.endswith('/'):
        value = '{}/'.format(value)
    return value


DEFAULT_SECRET_KEY = 'vc%m5g%w=dsntpj6k@ot!i9u1yv9jhq==1@=hdzz$v1-9!5b4d'
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', DEFAULT_SECRET_KEY)
RENDER_EXTERNAL_HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME')
RUNNING_ON_RENDER = bool(RENDER_EXTERNAL_HOSTNAME or os.getenv('RENDER'))
HAS_DATABASE_URL = bool(os.getenv('DATABASE_URL'))

DEBUG = env_bool(
    'DJANGO_DEBUG',
    default=not (
        os.getenv('DJANGO_ENV', '').strip().lower() == 'production'
        or RUNNING_ON_RENDER
        or HAS_DATABASE_URL
    ),
)

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', default=['127.0.0.1', 'localhost', 'testserver'])
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

if not DEBUG and SECRET_KEY == DEFAULT_SECRET_KEY:
    raise ImproperlyConfigured('Debe definir DJANGO_SECRET_KEY para produccion.')


INSTALLED_APPS = [
    'daphne',
    'channels',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'app.core.staticfiles.ProjectStaticFilesConfig',
    'widget_tweaks',
    'app.core.erp',
    'app.core.homepage',
    'app.core.login',
    'app.core.user.apps.UserConfig',
    'app.core.reports',
    'app.core.backup.apps.BackupConfig',
    'app.core.sync.apps.SyncConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'crum.CurrentRequestUserMiddleware',
]

ROOT_URLCONF = 'app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'app', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'app.wsgi.application'
ASGI_APPLICATION = 'app.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': os.getenv(
            'CHANNEL_LAYER_BACKEND',
            'channels.layers.InMemoryChannelLayer',
        ),
    },
}

DATABASES = db.get_databases(use_sqlite=False, debug=DEBUG)

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'es'
TIME_ZONE = os.getenv('DJANGO_TIME_ZONE', 'America/Tegucigalpa')
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Django 3.0 ignores this setting, so models also declare BigAutoField explicitly.
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles/')
STATICFILES_STORAGE = os.getenv(
    'DJANGO_STATICFILES_STORAGE',
    'whitenoise.storage.CompressedStaticFilesStorage',
)
USE_DATABASE_MEDIA_STORAGE = env_bool('DJANGO_USE_DATABASE_MEDIA_STORAGE', default=RUNNING_ON_RENDER or HAS_DATABASE_URL)
if USE_DATABASE_MEDIA_STORAGE:
    DEFAULT_FILE_STORAGE = 'app.core.user.storage.DatabaseMediaStorage'

LOGIN_REDIRECT_URL = '/erp/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'
LOGIN_URL = '/login/'

MEDIA_ROOT = os.getenv('DJANGO_MEDIA_ROOT', os.path.join(BASE_DIR, 'media/'))
MEDIA_URL = url_path(os.getenv('DJANGO_MEDIA_URL'), default='/media/')
SERVE_MEDIA = env_bool('DJANGO_SERVE_MEDIA', default=DEBUG or RUNNING_ON_RENDER or HAS_DATABASE_URL)

AUTH_USER_MODEL = 'user.User'

CSRF_TRUSTED_ORIGINS = [
    csrf_origin(origin)
    for origin in env_list('DJANGO_CSRF_TRUSTED_ORIGINS', default=[])
]
if RENDER_EXTERNAL_HOSTNAME:
    render_csrf_origin = csrf_origin(RENDER_EXTERNAL_HOSTNAME)
    if render_csrf_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_csrf_origin)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

if env_bool('DJANGO_USE_PROXY_SSL_HEADER', default=False):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', default=True)
    SESSION_COOKIE_SECURE = env_bool('DJANGO_SESSION_COOKIE_SECURE', default=True)
    CSRF_COOKIE_SECURE = env_bool('DJANGO_CSRF_COOKIE_SECURE', default=True)
    SECURE_HSTS_SECONDS = int(os.getenv('DJANGO_SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True)
    SECURE_HSTS_PRELOAD = env_bool('DJANGO_SECURE_HSTS_PRELOAD', default=True)
