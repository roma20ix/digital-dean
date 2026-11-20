import os

from .base import *

DEBUG = True
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or "django-insecure-development-only"
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": BASE_DIR / "db.sqlite3",
    # Проверка параллельных POST использует тот же файловый режим, что и runserver.
    "TEST": {"NAME": BASE_DIR / f".test-cabinet-{os.getpid()}.sqlite3"},
}}
