#!/usr/bin/env bash
set -o errexit
set -o pipefail

python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py bootstrap_access

exec python -m gunicorn app.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
