import os
from copy import deepcopy
from urllib.parse import parse_qsl, unquote, urlparse

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


def build_database_from_url(database_url):
    parsed_url = urlparse(database_url)
    engine_map = {
        'postgres': 'django.db.backends.postgresql',
        'postgresql': 'django.db.backends.postgresql',
        'pgsql': 'django.db.backends.postgresql',
        'mysql': 'django.db.backends.mysql',
        'mysql2': 'django.db.backends.mysql',
        'sqlite': 'django.db.backends.sqlite3',
        'sqlite3': 'django.db.backends.sqlite3',
    }

    scheme = parsed_url.scheme.split('+', 1)[0]
    if scheme not in engine_map:
        raise ImproperlyConfigured(
            'DATABASE_URL debe usar postgres://, postgresql://, mysql:// o sqlite:/// .'
        )

    if scheme in ('sqlite', 'sqlite3'):
        database_name = parsed_url.path
        if database_name.startswith('/'):
            database_name = database_name[1:]
        return {
            'default': {
                'ENGINE': engine_map[scheme],
                'NAME': database_name or os.path.join(BASE_DIR, 'db.sqlite3'),
            }
        }

    config = {
        'default': {
            'ENGINE': engine_map[scheme],
            'NAME': unquote(parsed_url.path.lstrip('/')),
            'USER': unquote(parsed_url.username or ''),
            'PASSWORD': unquote(parsed_url.password or ''),
            'HOST': parsed_url.hostname or '',
            'PORT': str(parsed_url.port or ''),
            'CONN_MAX_AGE': env_int('DJANGO_CONN_MAX_AGE', default=60),
        }
    }

    options = dict(parse_qsl(parsed_url.query))
    if options:
        config['default']['OPTIONS'] = options

    return config


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


def build_mysql_database():
    database_name = os.getenv('MYSQL_NAME')
    host = os.getenv('MYSQL_HOST')
    user = os.getenv('MYSQL_USER')

    if not database_name or not host or not user:
        raise ImproperlyConfigured(
            'MYSQL_NAME, MYSQL_HOST y MYSQL_USER son obligatorios cuando DJANGO_DB_ENGINE=mysql.'
        )

    options = {
        'charset': os.getenv('MYSQL_CHARSET', 'utf8mb4'),
        'init_command': os.getenv('MYSQL_INIT_COMMAND', "SET sql_mode='STRICT_TRANS_TABLES'"),
    }

    return {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': database_name,
            'USER': user,
            'PASSWORD': os.getenv('MYSQL_PASSWORD', ''),
            'HOST': host,
            'PORT': os.getenv('MYSQL_PORT', '3306'),
            'CONN_MAX_AGE': env_int('DJANGO_CONN_MAX_AGE', default=60),
            'OPTIONS': options,
        }
    }


def build_postgresql_database():
    database_name = os.getenv('POSTGRES_NAME')
    host = os.getenv('POSTGRES_HOST')
    user = os.getenv('POSTGRES_USER')

    if not database_name or not host or not user:
        raise ImproperlyConfigured(
            'POSTGRES_NAME, POSTGRES_HOST y POSTGRES_USER son obligatorios cuando DJANGO_DB_ENGINE=postgresql.'
        )

    return {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': database_name,
            'USER': user,
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
            'HOST': host,
            'PORT': os.getenv('POSTGRES_PORT', '5432'),
            'CONN_MAX_AGE': env_int('DJANGO_CONN_MAX_AGE', default=60),
            'OPTIONS': {
                'options': '-c timezone=UTC',
            },
        }
    }


def get_databases(use_sqlite=False, debug=False):
    database_url = os.getenv('DATABASE_URL')
    if database_url and not use_sqlite:
        return build_database_from_url(database_url)

    selected_engine = os.getenv('DJANGO_DB_ENGINE', 'sqlite').strip().lower()

    if use_sqlite or selected_engine == 'sqlite':
        return deepcopy(SQLITE)

    if selected_engine in ('postgres', 'pgsql'):
        selected_engine = 'postgresql'

    if selected_engine not in ('sqlserver', 'mysql', 'postgresql'):
        raise ImproperlyConfigured(
            'DJANGO_DB_ENGINE debe ser "sqlite", "sqlserver", "mysql" o "postgresql". Valor recibido: {}'.format(selected_engine)
        )

    if debug and not os.getenv('SQLSERVER_NAME'):
        if selected_engine == 'sqlserver':
            return deepcopy(SQLITE)

    if debug and not os.getenv('MYSQL_NAME'):
        if selected_engine == 'mysql':
            return deepcopy(SQLITE)

    if debug and not os.getenv('POSTGRES_NAME'):
        if selected_engine == 'postgresql':
            return deepcopy(SQLITE)

    if selected_engine == 'mysql':
        return build_mysql_database()

    if selected_engine == 'postgresql':
        return build_postgresql_database()

    return build_sqlserver_database()
