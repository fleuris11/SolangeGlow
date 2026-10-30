"""Boosts: a pro pays (module 5) to be shown first in the search and in the feed of her
city and trade, for a day or a week. A boost is a campaign like the others."""

from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from apps.core.audit.services import record
from apps.core.selectors import is_feature_enabled
from apps.notifications.services import notify
from apps.payments import services as payment_services
from apps.payments.models import Payment, Purpose
from apps.pros.models import ProProfile

from .. import errors
from ..models import Advertiser, Boost, Campaign, Creative, Placement
from . import common
from .delivery import stats_of

SOURCE = "boost"
B = Boost.Status
PS = Payment.Status
DAYS = {Boost.Duration.DAY: 1, Boost.Duration.WEEK: 7}
DEFAULT_PRICES = {
    "BJ": {"currency": "XOF", "day": 1000, "week": 5000},
    "FR": {"currency": "EUR", "day": 300, "week": 1500},
}


def prices(country) -> dict | None:
    """{"currency", "day", "week"} for the country of the pro, or None."""
    code = getattr(country, "code", None) or ""
    found = (common.setting("ads.boost_prices", DEFAULT_PRICES) or {}).get(code)
    if not found or not found.get("currency"):
        return None
    return found


def boosts_on(pro: ProProfile) -> bool:
    return is_feature_enabled("boosts", country=pro.country if pro.country_id else None)


def running(pro: ProProfile, now=None):
    now = now or timezone.now()
    return (
        Boost.objects.filter(pro=pro, status=B.ACTIVE, ends_at__gt=now).order_by("-ends_at").first()
    )


@transaction.atomic
def buy(pro: ProProfile, duration: str, *, actor) -> Boost:
    """The boost waiting for its payment, and its payment page."""
    if pro is None or pro.status != ProProfile.Status.PUBLISHED:
        raise errors.NotAPro()
    if not boosts_on(pro):
        raise errors.BoostsUnavailable()
    price = prices(pro.country)
    if price is None or duration not in DAYS or not price.get(duration):
        raise errors.NoBoostPrice()
    current = running(pro)
    if current is not None:
        until = timezone.localtime(current.ends_at).strftime("%d/%m/%Y %H:%M")
        raise errors.BoostRunning(details={"until": until})
    from apps.glowpro.selectors import house_account

    boost = Boost.objects.create(
        pro=pro, duration=duration, amount_minor=int(price[duration]), currency=price["currency"]
    )
    payment = payment_services.create_payment(
        pro.user,
        house_account(pro.country),
        purpose=Purpose.BOOST,
        items_minor=boost.amount_minor,
        currency=boost.currency,
        description=f"Boost — {pro.display_name}"[:200],
        delivery_mode=Payment.Delivery.SERVICE,
        source_type=SOURCE,
        source_id=boost.pk,
        with_buyer_fee=False,
    )
    boost.payment = payment
    boost.save(update_fields=["payment", "updated_at"])
    record("ads.boost_bought", boost, actor=actor, metadata={"duration": duration})
    payment_services.start_checkout(payment, buyer=pro.user)
    return boost


def may_cancel_payment(payment: Payment, actor) -> bool:
    return True  # an unpaid boost can be left: nothing is lost


def _advertiser(pro: ProProfile) -> Advertiser:
    found, _ = Advertiser.objects.get_or_create(
        pro=pro,
        defaults={"name": pro.display_name[:120], "kind": Advertiser.Kind.PRO},
    )
    return found


@transaction.atomic
def _activate(boost: Boost) -> Boost:
    boost = (
        Boost.objects.select_for_update(of=("self",))
        .select_related("pro__user", "pro__country")
        .get(pk=boost.pk)
    )
    if boost.status != B.WAITING_PAYMENT:
        return boost
    pro = boost.pro
    now = timezone.now()
    ends = now + datetime.timedelta(days=DAYS[boost.duration])
    campaign = Campaign.objects.create(
        advertiser=_advertiser(pro),
        name=f"Boost {pro.display_name}"[:120],
        kind=Campaign.Kind.BOOST,
        status=Campaign.Status.ACTIVE,
        starts_at=now,
        ends_at=ends,
        priority=int(common.setting("ads.boost_priority", 5)),
        price_minor=boost.amount_minor,
        currency=boost.currency,
        max_per_day=int(common.setting("ads.boost_max_per_day", 3)),
        countries=[pro.country.code] if pro.country_id else [],
        cities=[pro.city] if pro.city else [],
        trades=list(pro.trades.values_list("key", flat=True)),
    )
    placements = [
        p
        for p in common.setting("ads.boost_placements", [Placement.SEARCH, Placement.FEED]) or []
        if p in Placement.values
    ]
    Creative.objects.create(
        campaign=campaign,
        name=pro.display_name[:120],
        format=Creative.Format.NATIVE,
        placements=placements,
        pro=pro,
    )
    boost.campaign = campaign
    boost.status = B.ACTIVE
    boost.starts_at, boost.ends_at = now, ends
    boost.save(update_fields=["campaign", "status", "starts_at", "ends_at", "updated_at"])
    record("ads.boost_started", boost)
    transaction.on_commit(common.changed)
    until = timezone.localtime(ends).strftime("%d/%m %H:%M")
    notify(pro.user, "ads.boost_started", {"until": until}, link="/pro/boost")
    return boost


def on_payment_change(payment: Payment) -> None:
    """Paid: the money goes to the platform at once and the boost starts."""
    boost = Boost.objects.filter(payment=payment).first()
    if boost is None:
        return
    if payment.status == PS.HELD:
        payment_services.release(payment, reason="boost")
        _activate(boost)
    elif payment.status == PS.CANCELLED and boost.status == B.WAITING_PAYMENT:
        Boost.objects.filter(pk=boost.pk).update(status=B.CANCELLED)


def end_due(now=None) -> int:
    """Celery Beat: boosts past their time are ended; the pro gets her figures."""
    now = now or timezone.now()
    ended = 0
    for boost in Boost.objects.filter(status=B.ACTIVE, ends_at__lte=now).select_related(
        "pro__user", "campaign"
    ):
        Boost.objects.filter(pk=boost.pk).update(status=B.ENDED)
        figures = stats_of([boost.campaign]) if boost.campaign_id else {}
        notify(
            boost.pro.user,
            "ads.boost_ended",
            {"impressions": figures.get("impressions", 0), "clicks": figures.get("clicks", 0)},
            link="/pro/boost",
        )
        ended += 1
    return ended


def history(pro: ProProfile):
    return Boost.objects.filter(pro=pro).exclude(status=B.CANCELLED).select_related("campaign")
