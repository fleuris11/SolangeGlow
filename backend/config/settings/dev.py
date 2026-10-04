"""Local development settings (used by docker compose)."""

from .base import *  # noqa: F403
from .base import env

DEBUG = env.bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "0.0.0.0", "backend"]
)
CSRF_TRUSTED_ORIGINS = env.list(
    "DJANGO_CSRF_TRUSTED_ORIGINS", default=["http://localhost:8000", "http://localhost:3000"]
)

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
