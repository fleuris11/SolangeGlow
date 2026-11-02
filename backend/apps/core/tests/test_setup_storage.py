from io import StringIO

import httpx
import pytest
from botocore.exceptions import ClientError
from django.core.management import CommandError, call_command
from django.test import override_settings

from apps.core.management.commands import setup_storage

pytestmark = pytest.mark.django_db


class FakeS3:
    def __init__(self, error=None):
        self.error = error
        self.cors = None

    def put_bucket_cors(self, **kwargs):
        if self.error:
            raise ClientError({"Error": {"Code": self.error}}, "PutBucketCors")
        self.cors = kwargs


class FakeStorage:
    def __init__(self, prefix):
        self.prefix = prefix
        self.deleted = []

    def save(self, name, content):
        return name

    def url(self, name):
        return f"https://s3.test/{self.prefix}/{name}" + (
            "?sig=1" if self.prefix == "private" else ""
        )

    def delete(self, name):
        self.deleted.append(name)


@pytest.fixture
def world(monkeypatch):
    s3 = FakeS3()
    public, private = FakeStorage("public"), FakeStorage("private")
    answers = {"public": 200, "signed": 200, "unsigned": 403}

    def get(url, timeout):
        if "/public/" in url:
            return httpx.Response(answers["public"])
        return httpx.Response(answers["signed" if "sig=" in url else "unsigned"])

    monkeypatch.setattr(setup_storage, "_client", lambda: s3)
    monkeypatch.setattr(setup_storage, "public_storage", lambda: public)
    monkeypatch.setattr(setup_storage, "private_storage", lambda: private)
    monkeypatch.setattr(setup_storage.httpx, "get", get)
    return {"s3": s3, "public": public, "private": private, "answers": answers}


@override_settings(AWS_STORAGE_BUCKET_NAME="media", SITE_URL="https://solangeglow.com")
def test_sets_cors_for_the_site_and_proves_reads(world):
    out = StringIO()
    call_command("setup_storage", stdout=out)
    rule = world["s3"].cors["CORSConfiguration"]["CORSRules"][0]
    assert rule["AllowedOrigins"] == ["https://solangeglow.com"]
    assert "the bucket is ready" in out.getvalue()
    # Nothing left behind in the bucket.
    assert world["public"].deleted and world["private"].deleted


@override_settings(AWS_STORAGE_BUCKET_NAME="media")
def test_a_public_file_that_cannot_be_read_stops_here(world):
    world["answers"]["public"] = 403
    with pytest.raises(CommandError, match="MEDIA_PUBLIC_ACL"):
        call_command("setup_storage", stdout=StringIO())
    assert world["public"].deleted


@override_settings(AWS_STORAGE_BUCKET_NAME="media")
def test_a_private_file_open_to_anyone_stops_here(world):
    world["answers"]["unsigned"] = 200
    with pytest.raises(CommandError, match="without a signature"):
        call_command("setup_storage", stdout=StringIO())


@override_settings(AWS_STORAGE_BUCKET_NAME="media")
def test_a_broken_signed_link_stops_here(world):
    world["answers"]["signed"] = 403
    with pytest.raises(CommandError, match="signed link"):
        call_command("setup_storage", stdout=StringIO())


@override_settings(AWS_STORAGE_BUCKET_NAME="media")
def test_a_provider_refusing_cors_is_only_a_warning(world, monkeypatch):
    monkeypatch.setattr(setup_storage, "_client", lambda: FakeS3(error="NotImplemented"))
    out = StringIO()
    call_command("setup_storage", stdout=out)
    assert "CORS: not set (NotImplemented)" in out.getvalue()


@override_settings(AWS_STORAGE_BUCKET_NAME="")
def test_no_bucket_is_refused():
    with pytest.raises(CommandError):
        call_command("setup_storage", stdout=StringIO())
