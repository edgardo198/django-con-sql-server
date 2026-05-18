#!/usr/bin/env bash
set -o errexit

mkdir -p "${DJANGO_MEDIA_ROOT:-media}"
python manage.py migrate --noinput
python manage.py media_diagnostics || true
python manage.py bootstrap_access
python -m gunicorn app.wsgi:application --bind 0.0.0.0:${PORT:-8000}
