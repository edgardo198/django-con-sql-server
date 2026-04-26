import os
from copy import deepcopy

from django.core.exceptions import ImproperlyConfigured

try:
    import pyodbc
except ImportError:
    pyodbc = None


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


SQLITE = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.getenv('SQLITE_NAME', os.path.join(BASE_DIR, 'db.sqlite3')),
    }
}


def env_int(name, default=0):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ImproperlyConfigured('{} debe ser un numero entero.'.format(name))


def get_sqlserver_driver():
    configured_driver = os.getenv('SQLSERVER_DRIVER')
    if configured_driver:
        return configured_driver

    preferred_drivers = [
        'ODBC Driver 18 for SQL Server',
        'ODBC Driver 17 for SQL Server',
        'ODBC Driver 13 for SQL Server',
        'SQL Server Native Client 11.0',
        'SQL Server',
    ]

    if pyodbc is None:
        return preferred_drivers[-1]

    installed_drivers = set(pyodbc.drivers())
    for driver in preferred_drivers:
        if driver in installed_drivers:
            return driver
    return preferred_drivers[-1]


def build_sqlserver_database():
    database_name = os.getenv('SQLSERVER_NAME')
    host = os.getenv('SQLSERVER_HOST')

    if not database_name or not host:
        raise ImproperlyConfigured(
            'SQLSERVER_NAME y SQLSERVER_HOST son obligatorios cuando DJANGO_DB_ENGINE=sqlserver.'
        )

    driver = get_sqlserver_driver()
    return {
        'default': {
            'ENGINE': 'sql_server.pyodbc',
            'NAME': database_name,
            'USER': os.getenv('SQLSERVER_USER', ''),
            'PASSWORD': os.getenv('SQLSERVER_PASSWORD', ''),
            'HOST': host,
            'PORT': os.getenv('SQLSERVER_PORT', ''),
            'CONN_MAX_AGE': env_int('DJANGO_CONN_MAX_AGE', default=60),
            'OPTIONS': {
                'driver': driver,
                'host_is_server': driver == 'SQL Server',
            },
        }
    }


def get_databases(use_sqlite=False, debug=False):
    selected_engine = os.getenv('DJANGO_DB_ENGINE', 'sqlite').strip().lower()

    if use_sqlite or selected_engine == 'sqlite':
        return deepcopy(SQLITE)

    if selected_engine != 'sqlserver':
        raise ImproperlyConfigured(
            'DJANGO_DB_ENGINE debe ser "sqlite" o "sqlserver". Valor recibido: {}'.format(selected_engine)
        )

    if debug and not os.getenv('SQLSERVER_NAME'):
        return deepcopy(SQLITE)

    return build_sqlserver_database()
