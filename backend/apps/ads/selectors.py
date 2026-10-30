"""What the screens and the back office read about ads."""

from __future__ import annotations

from django.db.models import Sum
from django.utils.translation import gettext as _

from apps.core.media.services import asset_payload

from .models import AdStat, Campaign, Creative
from .services import boosts, common, tracking


def _media(asset):
    return asset_payload(asset) if asset is not None and asset.is_ready else None


def _first_photo(item):
    first = next(iter(item.photos.all()), None) if item is not None else None
    return _media(first.media) if first else None


def ad_payload(creative: Creative, placement: str) -> dict:
    pro = creative.pro
    product = None
    if creative.product_id:
        item = creative.product
        product = {
            "title": item.title,
            "price_minor": item.price_minor,
            "currency": item.currency,
            "photo": _first_photo(item),
            "seller": item.pro.display_name,
        }
    elif creative.selection_product_id:
        item = creative.selection_product
        product = {
            "title": item.title,
            "price_minor": item.price_xof,
            "currency": "XOF",
            "photo": _first_photo(item),
            "seller": str(_("France Selection")),
        }
    return {
        "id": creative.pk,
        "placement": placement,
        "format": creative.format,
        "sponsor": creative.campaign.advertiser.name,
        "house": creative.campaign.kind == Campaign.Kind.HOUSE,
        "title": creative.title or (pro.display_name if pro else ""),
        "text": creative.text,
        "cta": creative.cta,
        "click_url": f"/api/v1/ads/click/{tracking.click_token(creative, placement)}",
        "media": [
            payload
            for payload in (_media(item.media) for item in creative.media_items.all())
            if payload
        ],
        "pro": {
            "slug": pro.slug,
            "name": pro.display_name,
            "photo": _media(pro.photo),
            "city": pro.city,
            "trades": [{"key": t.key, "name": t.name} for t in pro.trades.all()],
            "rating_average": float(pro.rating_average) if pro.rating_average is not None else None,
            "rating_count": pro.rating_count,
            "verified": pro.is_verified,
        }
        if pro
        else None,
        "product": product,
    }


def filler_payload(placement: str) -> dict | None:
    if common.filler(placement) != "adsense":
        return None
    client = common.setting("ads.adsense_client", "") or ""
    slot = (common.setting("ads.adsense_slots", {}) or {}).get(placement, "")
    if not client or not slot:
        return None
    return {"client": client, "slot": slot}


def stats_rows(campaign: Campaign):
    """Per day and placement, for the back office and the export of the advertiser."""
    return (
        AdStat.objects.filter(campaign=campaign)
        .values("day", "placement")
        .annotate(
            impressions=Sum("impressions"), clicks=Sum("clicks"), conversions=Sum("conversions")
        )
        .order_by("day", "placement")
    )


def boost_payload(pro) -> dict:
    price = boosts.prices(pro.country) if pro.country_id else None
    current = boosts.running(pro)
    rows = []
    for boost in boosts.history(pro)[:20]:
        figures = (
            boosts.stats_of([boost.campaign])
            if boost.campaign_id
            else {"impressions": 0, "clicks": 0, "conversions": 0}
        )
        rows.append(
            {
                "id": boost.pk,
                "duration": boost.duration,
                "status": boost.status,
                "amount_minor": boost.amount_minor,
                "currency": boost.currency,
                "starts_at": boost.starts_at,
                "ends_at": boost.ends_at,
                "impressions": figures["impressions"],
                "clicks": figures["clicks"],
            }
        )
    return {
        "open": boosts.boosts_on(pro),
        "prices": {
            "currency": price["currency"],
            "day": int(price.get("day") or 0),
            "week": int(price.get("week") or 0),
        }
        if price
        else None,
        "running_until": current.ends_at if current else None,
        "boosts": rows,
    }
