"""Referrals: a personal link; the godmother and the goddaughter get their points after
the first purchase of the goddaughter (money released, so a refunded purchase gives
nothing), within a monthly limit for the godmother."""

from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from apps.payments.models import Payment

from .. import errors
from ..models import Action, GlowProfile, Referral
from . import points
from .common import require_games, setting


def link_path(profile: GlowProfile) -> str:
    return f"/invite/{profile.referral_code}"


def referrer_of(code: str):
    profile = (
        GlowProfile.objects.select_related("user")
        .filter(referral_code=(code or "").strip().upper(), user__is_active=True)
        .first()
    )
    if profile is None:
        raise errors.InvalidReferral()
    return profile.user


@transaction.atomic
def attach(referee, code: str) -> Referral:
    """The goddaughter's new account is linked to the link she came with."""
    require_games(referee)
    referrer = referrer_of(code)
    if referrer.pk == referee.pk:
        raise errors.OwnReferral()
    days = int(setting("glow.referral_window_days", 7))
    if referee.created_at < timezone.now() - datetime.timedelta(days=days):
        raise errors.ReferralTooLate(details={"days": days})
    if Referral.objects.filter(referee=referee).exists():
        raise errors.AlreadyReferred()
    # An account that already bought something is not a new client.
    if Payment.objects.filter(buyer=referee, status=Payment.Status.RELEASED).exists():
        raise errors.ReferralTooLate(details={"days": days})
    return Referral.objects.create(referrer=referrer, referee=referee)


def on_purchase(payment: Payment) -> bool:
    """First purchase of a goddaughter: both get their points (once)."""
    with transaction.atomic():
        referral = (
            Referral.objects.select_for_update()
            .select_related("referrer", "referee")
            .filter(referee_id=payment.buyer_id, rewarded_at__isnull=True)
            .first()
        )
        if referral is None:
            return False
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        most = int(setting("glow.referral_monthly_max", 10))
        rewarded = Referral.objects.filter(
            referrer=referral.referrer, rewarded_at__gte=month_start, capped=False
        ).count()
        referral.rewarded_at = now
        referral.payment = payment
        referral.capped = rewarded >= most
        referral.save(update_fields=["rewarded_at", "payment", "capped", "updated_at"])
        if not referral.capped:
            points.award(
                referral.referrer,
                Action.REFERRAL,
                key=f"referral:{referral.pk}",
                source_type="referral",
                source_id=referral.pk,
            )
        points.award(
            referral.referee,
            Action.REFERRED,
            key=f"referred:{referral.pk}",
            source_type="referral",
            source_id=referral.pk,
        )
    return True


def stats(user) -> dict:
    rows = Referral.objects.filter(referrer=user)
    return {"invited": rows.count(), "rewarded": rows.filter(rewarded_at__isnull=False).count()}
