import os
from datetime import timedelta
from urllib.parse import urlparse


def load_local_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    if not os.path.exists(env_path):
        return

    with open(env_path, encoding='utf-8') as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            name, value = line.split('=', 1)
            os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


load_local_env()


database_url_scheme = urlparse(os.getenv('DATABASE_URL', '')).scheme.split('+', 1)[0]
selected_db_engine = os.getenv('DJANGO_DB_ENGINE', '').strip().lower()

if selected_db_engine in ('postgres', 'postgresql', 'pgsql') or database_url_scheme in ('postgres', 'postgresql', 'pgsql'):
    try:
        from django.db.backends.postgresql import utils as postgresql_utils
        from django.utils.timezone import utc
    except ImportError:
        postgresql_utils = None

    if postgresql_utils is not None:
        def utc_tzinfo_factory(offset):
            if offset not in (0, timedelta(0)):
                raise AssertionError("database connection isn't set to UTC")
            return utc

        postgresql_utils.utc_tzinfo_factory = utc_tzinfo_factory


if selected_db_engine == 'mysql' or database_url_scheme in ('mysql', 'mysql2'):
    try:
        import pymysql
    except ImportError:
        pymysql = None

    if pymysql is not None:
        pymysql.install_as_MySQLdb()
