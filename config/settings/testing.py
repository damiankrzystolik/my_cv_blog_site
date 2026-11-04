from .base import *

DEBUG = False
SECRET_KEY = "test-secret-key-not-for-production"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Ten sam silnik co na produkcji — wyszukiwarka bloga używa pg_trgm, a SQLite różni się
# od Postgresa w zachowaniu zapytań (np. union() z ORDER BY).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="test_db"),
        "USER": config("DB_USER", default="test_user"),
        "PASSWORD": config("DB_PASSWORD", default="test_password"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

AXES_ENABLED = False

BLOG_COMMENT_NOTIFY_EMAILS = ["owner@example.com"]
