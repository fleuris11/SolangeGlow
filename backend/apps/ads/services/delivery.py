"""Which ads a screen shows: fast (the running ads of a placement are kept in the cache),
targeted, never more than allowed per person and per day, never more than allowed per
screen. Each ad sent is an impression."""

from __future__ import annotations

import secrets

from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import F, Sum
from django.utils import timezone

from ..models import AdStat, Campaign, Creative, Placement
from .common import Audience, ads_on, filler, max_per_screen, setting, version

K = Campaign.Kind


def _running(placement: str, now) -> list[dict]:
    """The creatives that may run in a placement (cached for `ads.cache_seconds`)."""
    key = f"ads:running:{placement}:{version()}"
    found = cache.get(key)
    if found is not None:
        return found
    creatives = (
        Creative.objects.filter(
            is_active=True,
            placements__contains=[placement],
            campaign__status=Campaign.Status.ACTIVE,
            campaign__ends_at__gt=now,
        )
        .select_related("campaign")
        .order_by("campaign_id", "created_at")
    )
    shown = dict(
        AdStat.objects.filter(campaign__status=Campaign.Status.ACTIVE)
        .values_list("campaign")
        .annotate(total=Sum("impressions"))
        .values_list("campaign", "total")
    )
    found = []
    for creative in creatives:
        campaign = creative.campaign
        found.append(
            {
                "creative": creative.pk,
                "campaign": campaign.pk,
                "kind": campaign.kind,
                "priority": campaign.priority,
                "starts": campaign.starts_at.timestamp(),
                "ends": campaign.ends_at.timestamp(),
                "max_per_day": campaign.max_per_day,
                "quota": campaign.impressions_bought,
                "shown": shown.get(campaign.pk, 0) or 0,
                "countries": [c.upper() for c in campaign.countries or []],
                "cities": [c.strip().lower() for c in campaign.cities or []],
                "languages": [c.lower() for c in campaign.languages or []],
                "roles": list(campaign.roles or []),
                "trades": list(campaign.trades or []),
            }
        )
    cache.set(key, found, int(setting("ads.cache_seconds", 60)))
    return found


def _targets(item: dict, audience: Audience, context: dict) -> bool:
    # A visitor whose country is not known yet is not kept out by the country.
    if item["countries"] and audience.country and audience.country.upper() not in item["countries"]:
        return False
    city = (context.get("city") or audience.city or "").strip().lower()
    if item["cities"] and city not in item["cities"]:
        return False
    if item["languages"] and audience.language.lower()[:2] not in item["languages"]:
        return False
    if item["roles"] and not (set(item["roles"]) & audience.roles):
        return False
    trades = {context["trade"]} if context.get("trade") else set(audience.trades)
    return not (item["trades"] and not (set(item["trades"]) & trades))


def _seen_key(campaign_id, viewer: str, day) -> str:
    return f"ads:seen:{campaign_id}:{viewer}:{day.isoformat()}"


def _served_key(campaign_id) -> str:
    return f"ads:served:{campaign_id}"


def _left_today(item: dict, audience: Audience, day) -> bool:
    if not audience.viewer:
        return True
    return (
        int(cache.get(_seen_key(item["campaign"], audience.viewer, day)) or 0) < item["max_per_day"]
    )


def _under_quota(item: dict) -> bool:
    if not item["quota"]:
        return True
    served = item["shown"] + int(cache.get(_served_key(item["campaign"])) or 0)
    return served < item["quota"]


def _draw(items: list[dict], count: int, rng) -> list[dict]:
    """One creative per campaign, drawn with the weight of the campaign's priority."""
    by_campaign: dict = {}
    for item in items:
        by_campaign.setdefault(item["campaign"], []).append(item)
    pool = [rng.choice(group) for group in by_campaign.values()]
    chosen = []
    while pool and len(chosen) < count:
        total = sum(item["priority"] for item in pool)
        ticket = rng.randrange(total)
        for index, item in enumerate(pool):
            if ticket < item["priority"]:
                chosen.append(pool.pop(index))
                break
            ticket -= item["priority"]
    return chosen


def count_impression(creative_id, campaign_id, placement: str, day) -> None:
    updated = AdStat.objects.filter(day=day, creative_id=creative_id, placement=placement).update(
        impressions=F("impressions") + 1, updated_at=timezone.now()
    )
    if not updated:
        try:
            with transaction.atomic():
                AdStat.objects.create(
                    day=day,
                    campaign_id=campaign_id,
                    creative_id=creative_id,
                    placement=placement,
                    impressions=1,
                )
        except IntegrityError:  # created meanwhile by another request
            AdStat.objects.filter(day=day, creative_id=creative_id, placement=placement).update(
                impressions=F("impressions") + 1
            )


def _remember(item: dict, audience: Audience, day) -> None:
    if audience.viewer:
        key = _seen_key(item["campaign"], audience.viewer, day)
        if not cache.add(key, 1, 60 * 60 * 26):
            cache.incr(key)
    seconds = int(setting("ads.cache_seconds", 60))
    if item["quota"] and not cache.add(_served_key(item["campaign"]), 1, seconds):
        cache.incr(_served_key(item["campaign"]))


def pick(
    placement: str,
    audience: Audience,
    *,
    count: int = 1,
    context: dict | None = None,
    exclude=(),
    now=None,
    rng=None,
) -> list[Creative]:
    """The ads of a screen, counted as shown. Sold campaigns and boosts first; house
    promotions only when nothing sold fits."""
    if placement not in Placement.values or not ads_on(audience):
        return []
    count = min(count, max_per_screen(placement))
    if count <= 0:
        return []
    now = now or timezone.now()
    moment = now.timestamp()
    day = timezone.localdate(now)
    context = context or {}
    fitting = [
        item
        for item in _running(placement, now)
        if item["starts"] <= moment < item["ends"]
        and item["creative"] not in exclude
        and _targets(item, audience, context)
        and _left_today(item, audience, day)
        and _under_quota(item)
    ]
    rng = rng or secrets.SystemRandom()
    paid = [item for item in fitting if item["kind"] != K.HOUSE]
    chosen = _draw(paid, count, rng)
    if not chosen and filler(placement) == "house":
        chosen = _draw([item for item in fitting if item["kind"] == K.HOUSE], count, rng)
    if not chosen:
        return []
    for item in chosen:
        _remember(item, audience, day)
        count_impression(item["creative"], item["campaign"], placement, day)
    creatives = {
        c.pk: c
        for c in Creative.objects.filter(pk__in=[item["creative"] for item in chosen])
        .select_related(
            "campaign__advertiser",
            "pro__user",
            "pro__photo",
            "product__pro",
            "selection_product",
        )
        .prefetch_related("media_items__media", "pro__trades")
    }
    return [creatives[item["creative"]] for item in chosen if item["creative"] in creatives]


def stats_of(campaigns) -> dict:
    rows = AdStat.objects.filter(campaign__in=campaigns).aggregate(
        impressions=Sum("impressions"), clicks=Sum("clicks"), conversions=Sum("conversions")
    )
    return {key: value or 0 for key, value in rows.items()}
