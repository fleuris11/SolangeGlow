"""Demo Glow Pro (development only, idempotent): Institut Prisca is Premium (her team of
four), Fatou Braids is on trial; Prisca has packages, stock, a gift card and a campaign."""

from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from apps.pros.models import ProProfile

from .models import Plan, Subscription, SubscriptionPeriod

PREMIUM = {
    "institut-prisca": Subscription.Status.ACTIVE,
    "fatou-braids": Subscription.Status.TRIALING,
}


def seed_glowpro() -> dict:
    counts = {"premium": 0, "salon": 0}
    plan = Plan.objects.filter(key="premium").first()
    if plan is None:
        return counts
    now = timezone.now()
    for pro in ProProfile.objects.filter(slug__in=PREMIUM):
        status = PREMIUM[pro.slug]
        days = 365 if status == Subscription.Status.ACTIVE else plan.trial_days
        subscription, created = Subscription.objects.get_or_create(
            pro=pro,
            defaults={
                "plan": plan,
                "status": status,
                "trial_used": True,
                "current_period_end": now + datetime.timedelta(days=days),
            },
        )
        if created:
            SubscriptionPeriod.objects.create(
                subscription=subscription,
                plan=plan,
                starts_at=now,
                ends_at=subscription.current_period_end,
                is_trial=status == Subscription.Status.TRIALING,
            )
        counts["premium"] += 1
    prisca = ProProfile.objects.filter(slug="institut-prisca").first()
    if prisca is not None:
        counts["salon"] = _salon(prisca)
    return counts


@transaction.atomic
def _salon(pro) -> int:
    from apps.salon.models import Campaign, GiftCard, Package
    from apps.salon.services import giftcards, stock

    if Package.objects.filter(pro=pro).exists():
        return 0
    services = list(pro.services.filter(is_active=True).order_by("position", "name"))
    if not services:
        return 0
    first = services[0]
    Package.objects.create(
        pro=pro,
        service=first,
        name=f"5 x {first.name}",
        sessions=5,
        price_minor=(first.price_minor or 10_000) * 4,
        currency=first.currency,
        max_installments=3,
    )
    for name, kind, unit, ean, quantity, threshold in (
        ("Huile de karité 250 ml", "retail", "piece", "4006381333931", 12, 3),
        ("Masque argile", "professional", "g", "", 900, 200),
        ("Lingettes démaquillantes", "professional", "piece", "", 2, 5),
    ):
        stock.save_item(
            pro,
            name=name,
            kind=kind,
            unit=unit,
            ean=ean,
            quantity=quantity,
            alert_threshold=threshold,
        )
    if not GiftCard.objects.filter(pro=pro).exists():
        giftcards.sell_on_site(
            pro, amount_minor=20_000, method="cash", actor=pro.user, recipient_name="Fifamè"
        )
    Campaign.objects.get_or_create(
        pro=pro,
        name="On te manque",
        defaults={
            "segment": Campaign.Segment.INACTIVE,
            "inactive_days": 60,
            "channel": "email",
            "subject": "{{ first_name }}, un soin t'attend",
            "body": "Bonjour {{ first_name }}, {{ pro }} a des places cette semaine.",
        },
    )
    return 1
