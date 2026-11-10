"""Production settings. Every secret comes from the environment."""

import os

from django.core.exceptions import ImproperlyConfigured

from config.prod_checks import unsafe_settings

from .base import *  # noqa: F403
from .base import env

DEBUG = False
ACCOUNTS_OTP_CONSOLE = False
ACCOUNTS_DEV_OTP_ENDPOINT = False
PROVIDERS_CONSOLE = False
PAYMENTS_FAKE_ENABLED = False
BACKOFFICE_REQUIRE_2FA = True
PAYMENTS_CLOSED_AT_START = True
API_DOCS_PUBLIC = False
AUTH_COOKIES = {**AUTH_COOKIES, "SECURE": True}

# Identity documents must not depend on SECRET_KEY (ADR-005): a key of their own.
IDENTITY_VAULT_KEY = env("IDENTITY_VAULT_KEY", default="")

_problems = unsafe_settings(
    secret_key=SECRET_KEY,
    allowed_hosts=ALLOWED_HOSTS,
    site_url=SITE_URL,
    internal_token=INTERNAL_API_TOKEN,
    vault_key=IDENTITY_VAULT_KEY,
    bucket=AWS_STORAGE_BUCKET_NAME,
    environ=os.environ,
)
if _problems:
    raise ImproperlyConfigured("Unsafe production settings:\n- " + "\n- ".join(_problems))

# The web server and the containers' health checks call the backend by its service name.
ALLOWED_HOSTS = [*ALLOWED_HOSTS, "backend"]
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[SITE_URL])

# Under ASGI a request has its own thread: kept connections would pile up until PostgreSQL
# refuses new ones (Django documentation, "Persistent connections"). A pool keeps a few open
# and lends them to the requests instead: no new connection to open on every API call.
# Each web worker has its own pool: workers x DATABASE_POOL_MAX stays under PostgreSQL's limit.
DATABASES["default"]["CONN_MAX_AGE"] = 0
DATABASES["default"].setdefault("OPTIONS", {})["pool"] = {
    "min_size": env.int("DATABASE_POOL_MIN", default=2),
    "max_size": env.int("DATABASE_POOL_MAX", default=10),
    "timeout": env.int("DATABASE_POOL_TIMEOUT", default=10),
}

# Serve static files (admin assets) straight from the application server.
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

# Caddy answers on the Internet: it redirects to HTTPS and says so in this header. The web
# server calls the backend directly over the private network: no redirect here.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=False)
SILENCED_SYSTEM_CHECKS = ["security.W008"]
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 365)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
LANGUAGE_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)

STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
