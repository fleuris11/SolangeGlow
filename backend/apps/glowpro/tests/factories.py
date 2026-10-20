"""Plans and subscriptions for the tests (the plans come from the reference data)."""

import datetime

from django.utils import timezone

from apps.glowpro.models import Plan, PlanPrice, Subscription


def premium_plan() -> Plan:
    return Plan.objects.get(key="premium")


def priced(pro, amount=9_900, currency="XOF") -> PlanPrice:
    price, _ = PlanPrice.objects.get_or_create(
        plan=premium_plan(),
        country=pro.country,
        defaults={"currency": currency, "amount_minor": amount},
    )
    return price


def premium(pro, days=30) -> Subscription:
    """The pro pays Premium (until in `days` days)."""
    subscription, _ = Subscription.objects.update_or_create(
        pro=pro,
        defaults={
            "plan": premium_plan(),
            "status": Subscription.Status.ACTIVE,
            "current_period_end": timezone.now() + datetime.timedelta(days=days),
        },
    )
    pro.__dict__.pop("_glowpro_subscription", None)
    return subscription
