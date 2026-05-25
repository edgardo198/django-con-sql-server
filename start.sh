#!/usr/bin/env bash
set -o errexit

mkdir -p "${DJANGO_MEDIA_ROOT:-media}"
python manage.py migrate --noinput
python manage.py media_diagnostics || true
python manage.py bootstrap_access --if-empty
python -m daphne -b 0.0.0.0 -p ${PORT:-8000} app.asgi:application
