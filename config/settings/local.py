import os

from .base import *

DEBUG = True
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or "django-insecure-development-only"
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": BASE_DIR / "db.sqlite3",
}}
