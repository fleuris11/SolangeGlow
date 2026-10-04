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

# Local http: cookies cannot be "Secure". Codes are printed in the backend logs.
AUTH_COOKIES = {**AUTH_COOKIES, "SECURE": env.bool("AUTH_COOKIE_SECURE", default=False)}
ACCOUNTS_OTP_CONSOLE = env.bool("ACCOUNTS_OTP_CONSOLE", default=True)
PROVIDERS_CONSOLE = env.bool("PROVIDERS_CONSOLE", default=True)
ACCOUNTS_DEV_OTP_ENDPOINT = env.bool("ACCOUNTS_DEV_OTP_ENDPOINT", default=True)
