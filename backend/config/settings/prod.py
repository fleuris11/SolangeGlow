"""Production settings. Every secret comes from the environment."""

from .base import *  # noqa: F403
from .base import env

DEBUG = False

# Serve static files (admin assets) straight from the application server.
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Solange Glow <no-reply@solangeglow.com>")

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Media on an S3-compatible object storage when a bucket is configured.
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
if AWS_STORAGE_BUCKET_NAME:
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default="") or None
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="") or None
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage"}
