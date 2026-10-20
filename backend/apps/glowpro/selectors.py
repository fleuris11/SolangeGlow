"""Which plan a pro is on, and what it allows. Every Premium feature asks here first."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.models import Country
from apps.core.selectors import get_setting

from . import errors
from .models import Plan, PlanPrice, Subscription

S = Subscription.Status


def default_plan() -> Plan:
    plan = Plan.objects.filter(is_default=True, is_active=True).first()
    if plan is None:  # never deleted in practice: the reference data creates it
        plan, _ = Plan.objects.get_or_create(
            key="free", defaults={"name": "Gratuit", "is_default": True, "limits": {"staff": 2}}
        )
    return plan


def subscription_of(pro) -> Subscription | None:
    found = getattr(pro, "_glowpro_subscription", "unset")
    if found == "unset":
        found = Subscription.objects.select_related("plan").filter(pro=pro).first()
        pro._glowpro_subscription = found
    return found


def is_paying(subscription: Subscription | None, now=None) -> bool:
    """Trial, paid month, or the days of grace after an unpaid month."""
    if subscription is None:
        return False
    now = now or timezone.now()
    if subscription.status in (S.TRIALING, S.ACTIVE):
        return subscription.current_period_end is None or subscription.current_period_end > now
    if subscription.status == S.PAST_DUE:
        return subscription.grace_until is not None and subscription.grace_until > now
    return False


def plan_of(pro) -> Plan:
    subscription = subscription_of(pro)
    if is_paying(subscription):
        return subscription.plan
    return default_plan()


def has_feature(pro, feature: str) -> bool:
    return feature in (plan_of(pro).features or [])


def require(pro, feature: str) -> None:
    if not has_feature(pro, feature):
        raise errors.PremiumRequired(details={"feature": feature})


def limit(pro, key: str):
    """A number of the plan (None: no limit)."""
    value = (plan_of(pro).limits or {}).get(key)
    return None if value is None else int(value)


def price_of(plan: Plan, country) -> PlanPrice | None:
    if country is None:
        return None
    return PlanPrice.objects.filter(plan=plan, country=country).first()


def offered_plans():
    return Plan.objects.filter(is_active=True).prefetch_related("prices").order_by("position")


def house_account(country):
    """The platform as the seller of subscriptions in a country (created the first time)."""
    code = getattr(country, "code", None) or "BJ"
    email = get_setting(
        "glowpro.house_email", country=country, default=f"glowpro.{code.lower()}@solangeglow.com"
    )
    User = get_user_model()
    user = User.objects.filter(email=email).first()
    if user is None:
        user = User.objects.create_user(
            email=email,
            first_name="Solange Glow Pro",
            country=Country.objects.filter(code=code).first(),
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user
