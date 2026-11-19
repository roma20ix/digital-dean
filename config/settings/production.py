import os

from django.core.exceptions import ImproperlyConfigured

from .base import *


def required(name):
    value = os.environ.get(name)
    if not value:
        raise ImproperlyConfigured(f"Задайте {name} для публикации.")
    return value


DEBUG = False
MIDDLEWARE = [MIDDLEWARE[0], "whitenoise.middleware.WhiteNoiseMiddleware", *MIDDLEWARE[1:]]
SECRET_KEY = required("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = [host.strip() for host in required("DJANGO_ALLOWED_HOSTS").split(",")]
if any(not host or "*" in host for host in ALLOWED_HOSTS):
    raise ImproperlyConfigured("Укажите конкретные имена хостов в DJANGO_ALLOWED_HOSTS.")
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": required("PGDATABASE"),
    "USER": required("PGUSER"),
    "PASSWORD": required("PGPASSWORD"),
    "HOST": required("PGHOST"),
    "PORT": os.environ.get("PGPORT") or "5432",
    "OPTIONS": {"sslmode": os.environ.get("PGSSLMODE") or "require"},
}}
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 3600
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
