#!/usr/bin/env bash
set -euo pipefail

export DJANGO_SETTINGS_MODULE=config.settings.production

python3 manage.py collectstatic --noinput
python3 manage.py migrate --noinput
python3 manage.py seed_demo

exec gunicorn config.wsgi:application --bind 0.0.0.0:80 --workers 1 --threads 2
