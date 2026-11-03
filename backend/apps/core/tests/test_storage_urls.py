"""Media links: same result as django-storages, without a new S3 client per thread."""

import threading
from urllib.parse import parse_qs, urlsplit

import pytest
from django.test import override_settings
from storages.backends.s3 import S3Storage

from apps.core.media import storage

S3 = {
    "AWS_S3_ENDPOINT_URL": "http://s3.test",
    "AWS_S3_REGION_NAME": "gra",
    "AWS_ACCESS_KEY_ID": "key",
    "AWS_SECRET_ACCESS_KEY": "secret",
    "AWS_S3_ADDRESSING_STYLE": "path",
    "MEDIA_PUBLIC_BASE_URL": "",
}


@pytest.fixture(autouse=True)
def fresh_client():
    storage._signing_client.cache_clear()
    yield
    storage._signing_client.cache_clear()


def _storage(cls):
    return cls(
        bucket_name="media",
        endpoint_url=S3["AWS_S3_ENDPOINT_URL"],
        region_name=S3["AWS_S3_REGION_NAME"],
        access_key=S3["AWS_ACCESS_KEY_ID"],
        secret_key=S3["AWS_SECRET_ACCESS_KEY"],
        addressing_style="path",
        signature_version="s3v4",
    )


@override_settings(**S3)
@pytest.mark.parametrize("name", ["a/b.webp", "a/b c.webp", "é/x+y.webp"])
def test_public_link_is_the_one_of_the_library(name):
    public = _storage(storage.PublicMediaStorage)
    assert public.url(name) == S3Storage.url(public, name)


@override_settings(**S3)
def test_signed_link_is_the_one_of_the_library():
    private = _storage(storage.PrivateMediaStorage)
    ours = urlsplit(private.url("a/b c.webp"))
    theirs = urlsplit(S3Storage.url(private, "a/b c.webp"))
    assert ours.netloc == theirs.netloc
    assert ours.path == theirs.path
    assert sorted(parse_qs(ours.query)) == sorted(parse_qs(theirs.query))
    assert parse_qs(ours.query)["X-Amz-Expires"] == parse_qs(theirs.query)["X-Amz-Expires"]


@override_settings(**S3)
def test_link_keeps_the_given_duration_and_the_public_base():
    private = _storage(storage.PrivateMediaStorage)
    assert "X-Amz-Expires=60" in private.url("a.webp", expire=60)
    with override_settings(MEDIA_PUBLIC_BASE_URL="/s3"):
        assert private.url("a.webp").startswith("/s3/media/private/a.webp?")
        assert _storage(storage.PublicMediaStorage).url("a.webp") == "/s3/media/public/a.webp"


@override_settings(**S3)
def test_a_new_thread_does_not_build_a_new_client(monkeypatch):
    private = _storage(storage.PrivateMediaStorage)
    built = []
    original = storage.boto3.session.Session

    def counting(*args, **kwargs):
        built.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(storage.boto3.session, "Session", counting)
    for _ in range(3):
        thread = threading.Thread(target=private.url, args=("a.webp",))
        thread.start()
        thread.join()
    assert len(built) == 1


@override_settings(**{**S3, "AWS_S3_ADDRESSING_STYLE": "virtual"})
def test_other_addressing_goes_through_the_library(monkeypatch):
    public = _storage(storage.PublicMediaStorage)
    monkeypatch.setattr(S3Storage, "url", lambda *args, **kwargs: "http://library/a.webp")
    assert public.url("a.webp") == "http://library/a.webp"
