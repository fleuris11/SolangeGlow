"""Upload, read and delete media. Every module goes through these functions."""

from __future__ import annotations

import mimetypes
import uuid

from django.db import transaction

from apps.core.selectors import get_setting

from . import errors
from .models import MediaAsset
from .purposes import PURPOSES
from .storage import private_storage, public_storage

MB = 1024 * 1024
DEFAULT_MAX_BYTES = {"image": 15 * MB, "video": 200 * MB, "audio": 10 * MB}


def guess_kind(uploaded) -> str | None:
    content_type = (
        getattr(uploaded, "content_type", "") or mimetypes.guess_type(uploaded.name)[0] or ""
    )
    family = content_type.split("/")[0]
    return {"image": "image", "video": "video", "audio": "audio"}.get(family)


def create_asset(*, owner, uploaded, purpose: str, kind: str | None = None) -> MediaAsset:
    """Stores the original (private) and schedules its processing.

    The real type is checked again by the pipeline: the browser can lie.
    """
    rule = PURPOSES.get(purpose)
    if rule is None:
        raise errors.UnknownPurpose()
    kind = kind or guess_kind(uploaded)
    if kind not in rule.kinds:
        raise errors.WrongKind()
    max_bytes = int(
        get_setting(f"media.{kind}_max_bytes", default=DEFAULT_MAX_BYTES.get(kind, 10 * MB))
    )
    if uploaded.size > max_bytes:
        raise errors.FileTooLarge(errors.FileTooLarge.message % {"size": max_bytes // MB})

    asset = MediaAsset(
        id=uuid.uuid4(),
        owner=owner,
        kind=kind,
        purpose=purpose,
        visibility=rule.visibility,
        original_name=(uploaded.name or "")[:255],
        content_type=(getattr(uploaded, "content_type", "") or "")[:100],
        size_bytes=uploaded.size,
    )
    asset.original.save(uploaded.name or "upload", uploaded, save=False)
    asset.save()

    from .tasks import process_media_asset

    transaction.on_commit(lambda: process_media_asset.delay(str(asset.pk)))
    return asset


def variant_url(asset: MediaAsset, name: str) -> str | None:
    """Public link, or a signed link valid a few minutes for private media."""
    variant = (asset.variants or {}).get(name)
    if not variant:
        return None
    if asset.visibility == MediaAsset.Visibility.PUBLIC:
        return public_storage().url(variant["path"])
    ttl = int(get_setting("media.signed_url_ttl_seconds", default=600))
    storage = private_storage()
    try:
        return storage.url(variant["path"], expire=ttl)
    except TypeError:  # storages without signed links (tests)
        return storage.url(variant["path"])


def asset_payload(asset: MediaAsset | None) -> dict | None:
    """What the web app needs to show a media: status, blur preview, links per variant."""
    if asset is None:
        return None
    return {
        "id": str(asset.pk),
        "kind": asset.kind,
        "status": asset.status,
        "error": asset.error or None,
        "blurhash": asset.blurhash or None,
        "width": asset.width,
        "height": asset.height,
        "duration": asset.duration_seconds,
        "urls": {name: variant_url(asset, name) for name in (asset.variants or {})}
        if asset.is_ready
        else {},
    }


def get_for_owner(asset_id, owner) -> MediaAsset:
    asset = MediaAsset.objects.filter(pk=asset_id).first()
    if asset is None or (asset.owner_id != owner.pk and asset.visibility != "public"):
        raise errors.MediaNotFound()
    return asset


def delete_asset(asset: MediaAsset) -> None:
    from .processing import remove_files

    remove_files(asset)
    asset.delete()
