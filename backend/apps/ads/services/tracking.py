"""Clicks (a signed link that counts, then sends to the advertiser's page) and
conversions (a purchase or an appointment a few days after a click)."""

from __future__ import annotations

import datetime

from django.core import signing
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from .. import errors
from ..models import AdClick, AdStat, Creative, Placement
from .common import setting

SALT = "ads.click"


def click_token(creative: Creative, placement: str) -> str:
    return signing.dumps({"c": str(creative.pk), "p": placement}, salt=SALT, compress=True)


def target_of(creative: Creative) -> str:
    """Where the click leads: the link of the creative, or the page of what it shows."""
    if creative.link:
        return creative.link
    if creative.pro_id:
        return f"/{creative.pro.slug}"
    if creative.product_id:
        return f"/{creative.product.pro.slug}/shop/{creative.product.slug}"
    if creative.selection_product_id:
        return f"/selection/{creative.selection_product.slug}"
    return "/"


def safe_link(link: str) -> bool:
    """A page of the app or an https address (never javascript:, never //other.site)."""
    link = (link or "").strip()
    if not link:
        return True
    if link.startswith("/"):
        return not link.startswith("//")
    return link.startswith("https://")


def _bump(field: str, creative: Creative, placement: str, day) -> None:
    updated = AdStat.objects.filter(day=day, creative=creative, placement=placement).update(
        **{field: F(field) + 1}, updated_at=timezone.now()
    )
    if not updated:
        try:
            with transaction.atomic():
                AdStat.objects.create(
                    day=day,
                    campaign_id=creative.campaign_id,
                    creative=creative,
                    placement=placement,
                    **{field: 1},
                )
        except IntegrityError:
            AdStat.objects.filter(day=day, creative=creative, placement=placement).update(
                **{field: F(field) + 1}
            )


def click(token: str, user=None) -> str:
    """Counts the click and returns where to go."""
    days = int(setting("ads.click_link_days", 7))
    try:
        data = signing.loads(token, salt=SALT, max_age=datetime.timedelta(days=days))
    except signing.BadSignature as exc:
        raise errors.AdNotFound() from exc
    placement = data.get("p")
    creative = (
        Creative.objects.select_related("campaign", "pro", "product__pro", "selection_product")
        .filter(pk=data.get("c"))
        .first()
    )
    if creative is None or placement not in Placement.values:
        raise errors.AdNotFound()
    _bump("clicks", creative, placement, timezone.localdate())
    AdClick.objects.create(
        campaign_id=creative.campaign_id,
        creative=creative,
        placement=placement,
        user=user if user is not None and user.is_authenticated else None,
    )
    target = target_of(creative)
    return target if safe_link(target) else "/"


@transaction.atomic
def convert(user, what: str) -> bool:
    """A purchase or a booking of a person: the last click of the last days counts once."""
    if user is None:
        return False
    since = timezone.now() - datetime.timedelta(days=int(setting("ads.conversion_days", 7)))
    found = (
        AdClick.objects.select_for_update()
        .select_related("creative")
        .filter(user=user, created_at__gte=since, converted_at__isnull=True)
        .order_by("-created_at")
        .first()
    )
    if found is None:
        return False
    found.converted_at = timezone.now()
    found.conversion = what[:60]
    found.save(update_fields=["converted_at", "conversion", "updated_at"])
    _bump("conversions", found.creative, found.placement, timezone.localdate())
    return True
