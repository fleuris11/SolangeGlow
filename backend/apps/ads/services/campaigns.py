"""Life of a campaign in the back office: checked before it runs, paused, resumed, ended
at its date or when the impressions bought are used."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.core.audit.services import record

from .. import errors
from ..models import AdStat, Campaign, Placement
from . import common
from .tracking import safe_link

S = Campaign.Status


def check(campaign: Campaign) -> None:
    if campaign.ends_at <= campaign.starts_at:
        raise errors.InvalidCampaign()
    creatives = [c for c in campaign.creatives.all() if c.is_active]
    usable = [
        c
        for c in creatives
        if c.placements and set(c.placements) <= set(Placement.values) and safe_link(c.link)
    ]
    if not usable:
        raise errors.InvalidCampaign()


def _move(campaign: Campaign, status: str, actor, action: str) -> Campaign:
    before = campaign.status
    campaign.status = status
    campaign.save(update_fields=["status", "updated_at"])
    record(
        f"ads.{action}", campaign, actor=actor, before={"status": before}, after={"status": status}
    )
    transaction.on_commit(common.changed)
    return campaign


@transaction.atomic
def activate(campaign: Campaign, *, actor) -> Campaign:
    campaign = Campaign.objects.select_for_update().get(pk=campaign.pk)
    check(campaign)
    return _move(campaign, S.ACTIVE, actor, "activated")


@transaction.atomic
def pause(campaign: Campaign, *, actor) -> Campaign:
    campaign = Campaign.objects.select_for_update().get(pk=campaign.pk)
    if campaign.status != S.ACTIVE:
        return campaign
    return _move(campaign, S.PAUSED, actor, "paused")


def shown(campaign: Campaign) -> int:
    return AdStat.objects.filter(campaign=campaign).aggregate(n=Sum("impressions"))["n"] or 0


def end_due(now=None) -> int:
    """Celery Beat: campaigns past their date, or whose impressions bought are used."""
    now = now or timezone.now()
    ended = 0
    for campaign in Campaign.objects.filter(status__in=[S.ACTIVE, S.PAUSED]):
        over = campaign.ends_at <= now
        used = campaign.impressions_bought and shown(campaign) >= campaign.impressions_bought
        if over or used:
            with transaction.atomic():
                _move(campaign, S.ENDED, None, "ended")
            ended += 1
    return ended
