"""Where media files live: one S3 bucket, a public prefix and a private prefix (ADR-002).

Two storage aliases are declared in settings.STORAGES:
- "media_public": readable by anyone (profile photos, published pictures);
- "media_private": signed, short-lived URLs only (originals, identity documents).
"""

from __future__ import annotations

from django.conf import settings
from django.core.files.storage import storages
from storages.backends.s3 import S3Storage


class _RewrittenUrlMixin:
    """Serves bucket URLs through MEDIA_PUBLIC_BASE_URL (e.g. "/s3" proxied by the site).

    The signature of a signed URL covers the host it was made for (the internal S3
    endpoint); the web proxy forwards to that host, so the signature stays valid.
    """

    def url(self, name, parameters=None, expire=None, http_method=None):
        url = super().url(name, parameters=parameters, expire=expire, http_method=http_method)
        endpoint = (settings.AWS_S3_ENDPOINT_URL or "").rstrip("/")
        base = settings.MEDIA_PUBLIC_BASE_URL.rstrip("/")
        if base and endpoint and url.startswith(endpoint):
            return base + url[len(endpoint) :]
        return url


class PublicMediaStorage(_RewrittenUrlMixin, S3Storage):
    location = "public"
    querystring_auth = False
    default_acl = None
    file_overwrite = False


class PrivateMediaStorage(_RewrittenUrlMixin, S3Storage):
    location = "private"
    querystring_auth = True
    default_acl = None
    file_overwrite = False


def public_storage():
    return storages["media_public"]


def private_storage():
    return storages["media_private"]
