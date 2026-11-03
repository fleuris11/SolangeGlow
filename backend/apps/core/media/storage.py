"""Where media files live: one S3 bucket, a public prefix and a private prefix (ADR-002).

Two storage aliases are declared in settings.STORAGES:
- "media_public": readable by anyone (profile photos, published pictures);
- "media_private": signed, short-lived URLs only (originals, identity documents).
"""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import quote

import boto3
from botocore.config import Config
from django.conf import settings
from django.core.files.storage import storages
from storages.backends.s3 import S3Storage
from storages.utils import clean_name


@lru_cache(maxsize=1)
def _signing_client():
    """One S3 client per process (clients are thread-safe), it signs without any network.

    Under ASGI each request has its own thread, and S3Storage keeps one client per thread:
    a new one for each request, 0.2 s of processor time, a whole feed slowed down by it.
    """
    return boto3.session.Session().client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        region_name=settings.AWS_S3_REGION_NAME,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=Config(
            signature_version=settings.AWS_S3_SIGNATURE_VERSION,
            s3={"addressing_style": settings.AWS_S3_ADDRESSING_STYLE},
        ),
    )


class _RewrittenUrlMixin:
    """Serves bucket URLs through MEDIA_PUBLIC_BASE_URL (e.g. "/s3" proxied by the site).

    The signature of a signed URL covers the host it was made for (the internal S3
    endpoint); the web proxy forwards to that host, so the signature stays valid.
    """

    def _bucket_url(self, name, parameters, expire, http_method):
        endpoint = (settings.AWS_S3_ENDPOINT_URL or "").rstrip("/")
        if not endpoint or settings.AWS_S3_ADDRESSING_STYLE != "path":
            return super().url(name, parameters=parameters, expire=expire, http_method=http_method)
        key = self._normalize_name(clean_name(name))
        if not self.querystring_auth:
            return f"{endpoint}/{self.bucket_name}/{quote(key)}"
        return _signing_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": key, **(parameters or {})},
            ExpiresIn=expire or self.querystring_expire,
            HttpMethod=http_method,
        )

    def url(self, name, parameters=None, expire=None, http_method=None):
        url = self._bucket_url(name, parameters, expire, http_method)
        endpoint = (settings.AWS_S3_ENDPOINT_URL or "").rstrip("/")
        base = settings.MEDIA_PUBLIC_BASE_URL.rstrip("/")
        if base and endpoint and url.startswith(endpoint):
            return base + url[len(endpoint) :]
        return url


class PublicMediaStorage(_RewrittenUrlMixin, S3Storage):
    location = "public"
    querystring_auth = False
    # OVH has object ACLs, not bucket policies: each public file says it is public.
    default_acl = settings.MEDIA_PUBLIC_ACL or None
    file_overwrite = False


class PrivateMediaStorage(_RewrittenUrlMixin, S3Storage):
    location = "private"
    querystring_auth = True
    default_acl = None
    file_overwrite = False


class IdentityVaultStorage(S3Storage):
    """Identity documents: their own prefix, files encrypted before upload, no public link."""

    location = "vault"
    querystring_auth = True
    default_acl = None
    file_overwrite = False


def public_storage():
    return storages["media_public"]


def private_storage():
    return storages["media_private"]


def identity_vault_storage():
    return storages["identity_vault"]
