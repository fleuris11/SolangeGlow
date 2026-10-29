"""The Glow wheel: one free spin a day, never paid, no purchase needed (a paid game would
be a lottery). The server draws: each prize has the chance weight / sum of the weights of
the prizes available to the person today (country, daily stock), nothing else."""

from __future__ import annotations

import secrets
from decimal import ROUND_HALF_UP, Decimal

from django.db import IntegrityError, transaction
from django.db.models import Count
from django.utils import translation

from apps.accounts.selectors import can_purchase
from apps.core.selectors import is_feature_enabled

from .. import errors
from ..models import Action, Voucher, WheelPrize, WheelSpin
from . import points, rewards
from .common import country_code, country_of, locked_profile, require_games, today

VOUCHERS = {WheelPrize.Kind.AMOUNT_OFF, WheelPrize.Kind.EXPRESS}


def wheel_on(user) -> bool:
    return is_feature_enabled("wheel", country=country_of(user))


def shown(user):
    """The slices of the wheel in her country (before the daily stocks)."""
    code = country_code(user)
    prizes = WheelPrize.objects.filter(is_active=True, weight__gt=0)
    return [p for p in prizes if not p.countries or code in p.countries]


def available(user, day) -> list[WheelPrize]:
    prizes = shown(user)
    given = dict(
        WheelSpin.objects.filter(day=day, prize__in=prizes)
        .values_list("prize")
        .annotate(n=Count("id"))
        .values_list("prize", "n")
    )
    adult = can_purchase(user)
    return [
        p
        for p in prizes
        if (p.daily_stock is None or given.get(p.pk, 0) < p.daily_stock)
        and (adult or p.kind not in VOUCHERS)
    ]


def chances(prizes: list[WheelPrize]) -> dict:
    """Chance of each prize in percent (what the person is told)."""
    total = sum(p.weight for p in prizes)
    return {
        p.pk: Decimal(p.weight * 100 / total).quantize(Decimal("0.1"), ROUND_HALF_UP)
        for p in prizes
    }


def draw(prizes: list[WheelPrize], rng) -> WheelPrize:
    """One prize, with the probability weight / total weight. ``rng`` has ``randrange``."""
    ticket = rng.randrange(sum(p.weight for p in prizes))
    for prize in prizes:
        if ticket < prize.weight:
            return prize
        ticket -= prize.weight
    raise errors.NoPrize()  # pragma: no cover - the ticket is always below the total


def spin(user, *, rng=None, now=None) -> WheelSpin:
    require_games(user)
    if not wheel_on(user):
        raise errors.WheelUnavailable()
    day = today(user, now)
    with transaction.atomic():
        locked_profile(user)  # one spin at a time for a person
        if WheelSpin.objects.filter(user=user, day=day).exists():
            raise errors.AlreadySpun()
        # Prizes with a daily stock are locked: two people never take the last one.
        list(WheelPrize.objects.select_for_update().filter(daily_stock__isnull=False))
        prizes = available(user, day)
        if not prizes:
            raise errors.NoPrize()
        prize = draw(prizes, rng or secrets.SystemRandom())
        with translation.override(user.preferred_language or "fr"):
            label = str(prize.label)
        result = WheelSpin(user=user, day=day, prize=prize, kind=prize.kind, label=label)
        try:
            with transaction.atomic():
                result.save()
        except IntegrityError as exc:
            raise errors.AlreadySpun() from exc
        if prize.kind == WheelPrize.Kind.POINTS:
            entry = points.award(
                user,
                Action.WHEEL,
                key=f"wheel:{user.pk}:{day}",
                points=prize.points,
                source_type="wheel",
                source_id=result.pk,
                now=now,
            )
            result.points = entry.amount if entry else 0
        elif prize.kind in VOUCHERS:
            result.voucher = rewards.create_voucher(
                user,
                kind=Voucher.Kind(prize.kind),
                origin=Voucher.Origin.WHEEL,
                amount_minor=prize.amount_off_minor,
                days=prize.validity_days,
            )
        result.save(update_fields=["points", "voucher", "updated_at"])
    return result


def state(user, *, now=None) -> dict:
    day = today(user, now)
    prizes = shown(user)
    left = available(user, day) if user is not None else prizes
    odds = chances(left) if left else {}
    done = WheelSpin.objects.filter(user=user, day=day).select_related("voucher").first()
    return {
        "open": wheel_on(user),
        "can_spin": wheel_on(user) and done is None and bool(left),
        "prizes": [{"prize": p, "chance": odds.get(p.pk, Decimal(0))} for p in prizes],
        "today": done,
    }
