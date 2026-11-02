"""Prepares the object storage and proves it works: run once with the real keys.

The bucket stays private (OVH has no bucket policies): pictures that anyone may see carry
the object ACL of MEDIA_PUBLIC_ACL, and CORS lets the web app keep lessons for offline use.
"""

from __future__ import annotations

import uuid

import boto3
import httpx
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management import BaseCommand, CommandError

from apps.core.media.storage import private_storage, public_storage

TIMEOUT_SECONDS = 15
CORS_MAX_AGE_SECONDS = 3600


def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        region_name=settings.AWS_S3_REGION_NAME,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


class Command(BaseCommand):
    help = "Set CORS on the media bucket and check public and private reads."

    def handle(self, *args, **options):
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        if not bucket:
            raise CommandError("AWS_STORAGE_BUCKET_NAME is empty.")
        self._cors(_client(), bucket)
        name = f"storage-check/{uuid.uuid4().hex}.txt"
        self._check_public(name)
        self._check_private(name)
        self.stdout.write(self.style.SUCCESS("setup_storage: the bucket is ready."))

    def _cors(self, client, bucket):
        try:
            client.put_bucket_cors(
                Bucket=bucket,
                CORSConfiguration={
                    "CORSRules": [
                        {
                            "AllowedOrigins": [settings.SITE_URL],
                            "AllowedMethods": ["GET", "HEAD"],
                            "AllowedHeaders": ["*"],
                            "MaxAgeSeconds": CORS_MAX_AGE_SECONDS,
                        }
                    ]
                },
            )
            self.stdout.write("  CORS: set")
        except ClientError as exc:
            # Some providers refuse the call and allow every origin (MinIO): not fatal.
            code = exc.response.get("Error", {}).get("Code", "")
            self.stdout.write(self.style.WARNING(f"  CORS: not set ({code})"))

    def _check_public(self, name):
        storage = public_storage()
        saved = storage.save(name, ContentFile(b"public"))
        try:
            answer = httpx.get(storage.url(saved), timeout=TIMEOUT_SECONDS)
            if answer.status_code != 200:
                raise CommandError(
                    f"A public file cannot be read without a key (HTTP {answer.status_code}): "
                    "check MEDIA_PUBLIC_ACL and MEDIA_PUBLIC_BASE_URL."
                )
            self.stdout.write("  public file: readable by anyone")
        finally:
            storage.delete(saved)

    def _check_private(self, name):
        storage = private_storage()
        saved = storage.save(name, ContentFile(b"private"))
        try:
            signed = storage.url(saved)
            if httpx.get(signed, timeout=TIMEOUT_SECONDS).status_code != 200:
                raise CommandError("A private file cannot be read with its signed link.")
            if httpx.get(signed.split("?")[0], timeout=TIMEOUT_SECONDS).status_code == 200:
                raise CommandError("A private file can be read without a signature: stop here.")
            self.stdout.write("  private file: signed link only")
        finally:
            storage.delete(saved)
