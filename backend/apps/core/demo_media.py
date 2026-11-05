"""Puts the real photographs on the demo accounts (seed_demo, development only)."""

from __future__ import annotations

import uuid
from pathlib import PurePosixPath

from django.core.files.base import ContentFile

from apps.academy.models import Course
from apps.ads.models import CreativeMedia
from apps.core import demo_photos
from apps.core.media.models import MediaAsset
from apps.core.media.processing import process
from apps.pros.models import ProProfile
from apps.selection_france.models import SelectionPhoto
from apps.shop.models import ProductPhoto
from apps.social import demo_art
from apps.social.models import PostMedia, Story


def _trade(pro: ProProfile) -> str:
    first = pro.trades.first()
    return first.key if first else "hair"


def _new_asset(owner, seed: str, purpose: str, data: bytes) -> MediaAsset:
    asset = MediaAsset(
        id=uuid.uuid4(),
        owner=owner,
        kind=MediaAsset.Kind.IMAGE,
        purpose=purpose,
        visibility=MediaAsset.Visibility.PUBLIC,
        original_name=f"{seed}.jpg",
        content_type="image/jpeg",
        size_bytes=len(data),
    )
    asset.original.save(f"{seed}.jpg", ContentFile(data), save=False)
    asset.save()
    process(asset)
    return asset


def seed_pro_photos() -> int:
    """A portrait and a cover for the published showcases that have none."""
    done = 0
    pros = ProProfile.objects.filter(status=ProProfile.Status.PUBLISHED).select_related("user")
    for pro in pros:
        changed = []
        trade = _trade(pro)
        if pro.photo_id is None:
            data = demo_photos.portrait(pro.slug, trade)
            if data:
                pro.photo = _new_asset(pro.user, f"photo-{pro.slug}", "pro_photo", data)
                changed.append("photo")
        if pro.cover_id is None:
            data = demo_photos.look(f"cover-{pro.slug}", trade)
            if data:
                pro.cover = _new_asset(pro.user, f"cover-{pro.slug}", "pro_cover", data)
                changed.append("cover")
        if changed:
            pro.save(update_fields=changed)
            done += 1
    return done


def seed_course_covers() -> int:
    """A real photograph on the courses that have no cover."""
    done = 0
    for course in Course.objects.filter(cover__isnull=True).select_related("author"):
        trade = demo_photos._pick(list(demo_photos.TRADES), course.slug)
        data = demo_photos.look(f"course-{course.slug}", trade)
        if data:
            course.cover = _new_asset(course.author, f"course-{course.slug}", "course_cover", data)
            course.save(update_fields=["cover"])
            done += 1
    return done


def _replace(asset: MediaAsset, data: bytes | None) -> int:
    if not data:
        return 0
    asset.original.save(asset.original_name or f"{asset.pk}.jpg", ContentFile(data), save=False)
    asset.size_bytes = len(data)
    asset.content_type = "image/jpeg"
    asset.save(update_fields=["original", "size_bytes", "content_type"])
    process(asset)
    return 1


def refresh_photos() -> int:
    """Existing demo databases: the drawn pictures become photographs, in place."""
    count = 0
    trades = {pro.user_id: _trade(pro) for pro in ProProfile.objects.prefetch_related("trades")}
    media = list(
        PostMedia.objects.select_related("media").values_list("media_id", flat=True)
    ) + list(Story.objects.values_list("media_id", flat=True))
    media += list(CreativeMedia.objects.values_list("media_id", flat=True))
    for asset in MediaAsset.objects.filter(pk__in=media, kind=MediaAsset.Kind.IMAGE):
        seed = PurePosixPath(asset.original_name or str(asset.pk)).stem
        count += _replace(asset, demo_art.picture(seed, trades.get(asset.owner_id, "hair")))
    for model in (ProductPhoto, SelectionPhoto):
        for photo in model.objects.select_related("media"):
            drawing = demo_photos._pick(list(demo_photos.PRODUCTS), str(photo.media_id))
            count += _replace(photo.media, demo_photos.product(str(photo.media_id), drawing))
    return count + seed_pro_photos() + seed_course_covers()
