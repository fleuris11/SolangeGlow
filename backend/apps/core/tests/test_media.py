import io
import subprocess
from pathlib import Path

import pytest
from django.core.files.storage import storages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.core.media import errors, services
from apps.core.media.models import MediaAsset
from apps.core.media.tasks import process_media_asset

from .factories import PlatformSettingFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner():
    return User.objects.create_user(phone="+2290197123456")


def picture(size=(2000, 1500), fmt="JPEG", mode="RGB") -> bytes:
    image = Image.new(mode, size, (200, 16, 46, 255)[: len(mode)])
    exif = Image.Exif()
    exif.get_ifd(0x8825)[2] = (6.0, 21.0, 0.0)
    buffer = io.BytesIO()
    image.save(buffer, fmt, **({"exif": exif} if fmt == "JPEG" else {}))
    return buffer.getvalue()


def ffmpeg_file(tmp_path: Path, name: str, arguments: list[str]) -> bytes:
    output = tmp_path / name
    subprocess.run(  # noqa: S603
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *arguments, str(output)],  # noqa: S607
        check=True,
        capture_output=True,
    )
    return output.read_bytes()


def upload(data: bytes, name: str, content_type: str):
    return SimpleUploadedFile(name, data, content_type=content_type)


# --- Images --------------------------------------------------------------------------


def test_picture_gets_three_webp_sizes_without_metadata(owner):
    asset = services.create_asset(
        owner=owner, uploaded=upload(picture(), "p.jpg", "image/jpeg"), purpose="post"
    )

    asset.refresh_from_db()
    assert asset.status == MediaAsset.Status.READY
    assert asset.width == 2000
    assert {name: v["width"] for name, v in asset.variants.items()} == {
        "thumb": 160,
        "medium": 640,
        "large": 1280,
    }
    assert asset.blurhash
    with storages["media_public"].open(asset.variants["large"]["path"], "rb") as handle:
        image = Image.open(handle)
        assert image.format == "WEBP"
        assert not image.getexif()


def test_small_picture_is_never_enlarged(owner):
    asset = services.create_asset(
        owner=owner, uploaded=upload(picture((300, 200)), "p.jpg", "image/jpeg"), purpose="post"
    )

    asset.refresh_from_db()
    assert asset.variants["large"]["width"] == 300


def test_transparent_png_is_accepted(owner):
    data = picture((400, 400), fmt="PNG", mode="RGBA")
    asset = services.create_asset(
        owner=owner, uploaded=upload(data, "p.png", "image/png"), purpose="post"
    )

    asset.refresh_from_db()
    assert asset.status == MediaAsset.Status.READY


def test_sizes_come_from_settings(owner):
    PlatformSettingFactory(
        key="media.image_sizes", value_type="json", value='{"thumb": 100, "large": 900}'
    )
    asset = services.create_asset(
        owner=owner, uploaded=upload(picture(), "p.jpg", "image/jpeg"), purpose="post"
    )

    asset.refresh_from_db()
    assert set(asset.variants) == {"thumb", "large"}
    assert asset.variants["large"]["width"] == 900


def test_fake_picture_is_rejected(owner):
    asset = services.create_asset(
        owner=owner, uploaded=upload(b"GIF89a not really", "p.gif", "image/gif"), purpose="post"
    )

    asset.refresh_from_db()
    assert asset.status == MediaAsset.Status.REJECTED
    assert asset.error == "invalid_image"
    assert services.asset_payload(asset)["urls"] == {}


def test_private_media_live_in_the_private_storage(owner):
    asset = services.create_asset(
        owner=owner,
        uploaded=upload(picture(), "id.jpg", "image/jpeg"),
        purpose="identity_document",
    )

    asset.refresh_from_db()
    assert asset.visibility == "private"
    path = asset.variants["medium"]["path"]
    assert storages["media_private"].exists(path)
    assert not storages["media_public"].exists(path)


# --- Rules ---------------------------------------------------------------------------


def test_unknown_purpose_and_wrong_kind_are_refused(owner):
    with pytest.raises(errors.UnknownPurpose):
        services.create_asset(
            owner=owner, uploaded=upload(picture(), "p.jpg", "image/jpeg"), purpose="nope"
        )
    with pytest.raises(errors.WrongKind):
        services.create_asset(
            owner=owner, uploaded=upload(picture(), "p.jpg", "image/jpeg"), purpose="voice_note"
        )


def test_size_limit_comes_from_settings(owner):
    PlatformSettingFactory(key="media.image_max_bytes", value="1000")

    with pytest.raises(errors.FileTooLarge):
        services.create_asset(
            owner=owner, uploaded=upload(picture(), "p.jpg", "image/jpeg"), purpose="post"
        )


def test_processing_is_idempotent(owner):
    asset = services.create_asset(
        owner=owner, uploaded=upload(picture(), "p.jpg", "image/jpeg"), purpose="post"
    )
    asset.refresh_from_db()
    variants = asset.variants

    assert process_media_asset(str(asset.pk)) == "ready"
    asset.refresh_from_db()
    assert asset.variants == variants


# --- Video and audio (real ffmpeg) ---------------------------------------------------


def test_video_gets_two_qualities_and_a_poster(owner, tmp_path):
    data = ffmpeg_file(
        tmp_path,
        "clip.mp4",
        [
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=1280x720:rate=15:duration=2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            "-shortest",
        ],
    )
    asset = services.create_asset(
        owner=owner, uploaded=upload(data, "clip.mp4", "video/mp4"), purpose="itinerary_video"
    )

    asset.refresh_from_db()
    assert asset.status == MediaAsset.Status.READY, asset.error
    assert 1.5 < asset.duration_seconds < 2.5
    assert {"low", "medium", "poster_thumb", "poster_medium", "poster_large"} <= set(asset.variants)
    assert asset.variants["low"]["content_type"] == "video/mp4"
    assert asset.variants["low"]["bytes"] < asset.variants["medium"]["bytes"]
    assert asset.blurhash


def test_too_long_video_is_rejected(owner, tmp_path):
    PlatformSettingFactory(key="media.video_max_seconds", value="1")
    data = ffmpeg_file(
        tmp_path, "clip.mp4", ["-f", "lavfi", "-i", "testsrc=size=320x240:rate=10:duration=3"]
    )
    asset = services.create_asset(
        owner=owner, uploaded=upload(data, "clip.mp4", "video/mp4"), purpose="itinerary_video"
    )

    asset.refresh_from_db()
    assert asset.status == MediaAsset.Status.REJECTED
    assert asset.error == "too_long"


def test_voice_note_is_converted_to_opus(owner, tmp_path):
    data = ffmpeg_file(
        tmp_path, "voice.wav", ["-f", "lavfi", "-i", "sine=frequency=300:duration=3"]
    )
    asset = services.create_asset(
        owner=owner, uploaded=upload(data, "voice.wav", "audio/wav"), purpose="voice_note"
    )

    asset.refresh_from_db()
    assert asset.status == MediaAsset.Status.READY, asset.error
    assert asset.variants["voice"]["content_type"] == "audio/webm"
    assert storages["media_private"].exists(asset.variants["voice"]["path"])


def test_unreadable_audio_is_rejected(owner):
    asset = services.create_asset(
        owner=owner, uploaded=upload(b"not audio", "v.webm", "audio/webm"), purpose="voice_note"
    )

    asset.refresh_from_db()
    assert asset.status == MediaAsset.Status.REJECTED


# --- API -----------------------------------------------------------------------------


def test_upload_api_and_owner_only_access(owner):
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        reverse("v1:media-upload"),
        {"file": upload(picture(), "p.jpg", "image/jpeg"), "purpose": "identity_document"},
        format="multipart",
    )
    assert response.status_code == 202
    asset_id = response.json()["id"]

    detail = client.get(reverse("v1:media-detail", args=[asset_id]))
    assert detail.json()["status"] == "ready"
    assert set(detail.json()["urls"]) == {"thumb", "medium", "large"}

    stranger = APIClient()
    stranger.force_authenticate(User.objects.create_user(email="x@example.com"))
    assert stranger.get(reverse("v1:media-detail", args=[asset_id])).status_code == 404


def test_upload_api_refuses_unknown_purpose(owner):
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        reverse("v1:media-upload"),
        {"file": upload(picture(), "p.jpg", "image/jpeg"), "purpose": "anything"},
        format="multipart",
    )

    assert response.status_code == 400
