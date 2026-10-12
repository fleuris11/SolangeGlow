"""Cards shared in a conversation: a post, a service, a free slot, later a product.

Each kind has a resolver that checks the item is visible to the sender and returns a copy
of what the card shows. The shop registers the "product" resolver when it exists.
"""

from __future__ import annotations

import datetime
from collections.abc import Callable

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.core.media.services import asset_payload

from . import errors

Resolver = Callable[[object, dict], tuple[object, dict]]
_resolvers: dict[str, Resolver] = {}


def register(kind: str, resolver: Resolver) -> None:
    _resolvers[kind] = resolver


def unregister(kind: str) -> None:
    _resolvers.pop(kind, None)


def resolve(sender, kind: str, data: dict) -> tuple[object, dict]:
    """Returns (id of the item, copy for the card). Raises when it cannot be shared."""
    resolver = _resolvers.get(kind)
    if resolver is None:
        raise errors.ShareUnavailable()
    return resolver(sender, data)


def _picture(asset) -> dict | None:
    return asset_payload(asset) if asset is not None and asset.is_ready else None


def _post(sender, data: dict):
    from apps.social.feed import live_posts, visible_to

    post = (
        visible_to(sender, live_posts())
        .select_related("author", "pro")
        .filter(pk=data.get("id"))
        .first()
    )
    if post is None:
        raise errors.ShareNotFound()
    first = post.media_items.select_related("media").order_by("position").first()
    pro = post.pro if post.pro and post.pro.is_published else None
    return post.pk, {
        "title": (pro.display_name if pro else "") or post.author.first_name,
        "text": post.caption[:200],
        "picture": _picture(first.media if first else None),
        "link": f"/p/{post.pk}",
    }


def _service(sender, data: dict):
    from apps.pros.selectors import visible_services

    service = (
        visible_services()
        .select_related("pro")
        .filter(pk=data.get("id"), pro__status="published")
        .first()
    )
    if service is None:
        raise errors.ShareNotFound()
    photo = service.photos.select_related("media").first()
    return service.pk, {
        "title": service.name,
        "text": service.pro.display_name,
        "picture": _picture(photo.media if photo else None),
        "price_kind": service.price_kind,
        "amount_minor": service.price_minor,
        "currency": service.currency,
        "duration_minutes": service.duration_minutes,
        "link": f"/{service.pro.slug}#services",
    }


def _slot(sender, data: dict):
    """A free time of a pro, shared by her or by a client who saw it."""
    from apps.pros.models import ProProfile

    pro = ProProfile.objects.filter(slug=data.get("pro"), status="published").first()
    starts_at = parse_datetime(str(data.get("starts_at") or ""))
    if pro is None or starts_at is None:
        raise errors.ShareNotFound()
    if timezone.is_naive(starts_at):
        raise errors.ShareNotFound()
    now = timezone.now()
    if not now - datetime.timedelta(minutes=30) <= starts_at <= now + datetime.timedelta(days=60):
        raise errors.ShareNotFound()
    return pro.pk, {
        "title": pro.display_name,
        "starts_at": starts_at.isoformat(),
        "picture": _picture(pro.photo),
        "link": f"/{pro.slug}",
    }


register("post", _post)
register("service", _service)
register("slot", _slot)
