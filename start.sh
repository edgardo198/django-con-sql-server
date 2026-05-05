#!/usr/bin/env bash
set -o errexit

python manage.py migrate --noinput
python manage.py bootstrap_access
python -m gunicorn app.wsgi:application --bind 0.0.0.0:${PORT:-8000}
