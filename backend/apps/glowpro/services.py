"""The life of a Glow Pro subscription: free trial, monthly payment through the secure
payment (the platform sells, the money is released at once), renewal, days of grace, back
to the free plan (nothing is deleted; extra people of the agenda are paused)."""

from __future__ import annotations

import calendar
import datetime
import re

from django.db import transaction
from django.utils import timezone

from apps.core.audit.services import record
from apps.core.selectors import get_setting
from apps.notifications.services import notify
from apps.payments import services as payment_services
from apps.payments.models import Payment, Purpose

from . import errors, selectors
from .models import Feature, Plan, Subscription, SubscriptionPeriod, Widget

SOURCE = "glowpro"
S = Subscription.Status
PS = Payment.Status
LINK = "/pro/plan"


def add_month(moment: datetime.datetime) -> datetime.datetime:
    """Same day next month, local time (the last day when the month is shorter)."""
    moment = timezone.localtime(moment)
    year, month = (moment.year + 1, 1) if moment.month == 12 else (moment.year, moment.month + 1)
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


def _setting(key: str, pro, default):
    return get_setting(key, country=pro.country, default=default)


def subscription_for(pro) -> Subscription:
    subscription, _ = Subscription.objects.select_related("plan").get_or_create(
        pro=pro, defaults={"plan": selectors.default_plan(), "status": S.ENDED}
    )
    pro._glowpro_subscription = subscription
    return subscription


def _plan(pro, key: str) -> Plan:
    plan = Plan.objects.filter(key=key, is_active=True, is_default=False).first()
    if plan is None:
        raise errors.PlanNotFound()
    return plan


def _locked(pro) -> Subscription:
    subscription_for(pro)
    found = (
        Subscription.objects.select_for_update(of=("self",))
        .select_related("plan", "pro", "renewal_payment", "next_plan")
        .get(pro=pro)
    )
    pro._glowpro_subscription = found
    return found


@transaction.atomic
def start_trial(pro, plan_key: str = "premium", *, actor=None) -> Subscription:
    plan = _plan(pro, plan_key)
    subscription = _locked(pro)
    if selectors.is_paying(subscription):
        raise errors.AlreadyPremium()
    if subscription.trial_used or not plan.trial_days:
        raise errors.TrialUsed()
    now = timezone.now()
    # Counted on the local calendar: a change to winter time does not end it a day early.
    end = timezone.localtime(now) + datetime.timedelta(days=plan.trial_days)
    subscription.plan = plan
    subscription.status = S.TRIALING
    subscription.trial_used = True
    subscription.current_period_end = end
    subscription.grace_until = None
    subscription.cancel_at_period_end = False
    subscription.save()
    SubscriptionPeriod.objects.create(
        subscription=subscription, plan=plan, starts_at=now, ends_at=end, is_trial=True
    )
    record("glowpro.trial_started", subscription, actor=actor)
    transaction.on_commit(
        lambda: notify(
            pro.user, "glowpro.trial_started", {"plan": plan.name, "days": plan.trial_days},
            link=LINK,
        )
    )  # fmt: skip
    return subscription


def _new_payment(subscription: Subscription, plan: Plan) -> Payment:
    pro = subscription.pro
    price = selectors.price_of(plan, pro.country)
    if price is None:
        raise errors.PlanNotFound()
    payment = payment_services.create_payment(
        pro.user,
        selectors.house_account(pro.country),
        purpose=Purpose.SUBSCRIPTION,
        items_minor=price.amount_minor,
        currency=price.currency,
        description=f"Glow Pro {plan.name} — {pro.display_name}"[:200],
        delivery_mode=Payment.Delivery.SERVICE,
        source_type=SOURCE,
        source_id=subscription.pk,
    )
    subscription.renewal_payment = payment
    subscription.next_plan = plan
    subscription.save(update_fields=["renewal_payment", "next_plan", "updated_at"])
    return payment


@transaction.atomic
def subscribe(pro, plan_key: str = "premium", *, actor=None) -> Payment:
    """The payment page of the next month (the same one while it is waiting)."""
    plan = _plan(pro, plan_key)
    subscription = _locked(pro)
    if (
        subscription.status == S.ACTIVE
        and subscription.plan_id == plan.pk
        and not (subscription.renewal_payment_id or subscription.cancel_at_period_end)
    ):
        raise errors.AlreadyPremium()
    payment = subscription.renewal_payment
    if (
        payment is None
        or payment.status != PS.PENDING_PAYMENT
        or subscription.next_plan_id != plan.pk
    ):
        payment = _new_payment(subscription, plan)
    subscription.cancel_at_period_end = False
    subscription.save(update_fields=["cancel_at_period_end", "updated_at"])
    record("glowpro.checkout", subscription, actor=actor)
    return payment_services.start_checkout(payment, buyer=pro.user)


@transaction.atomic
def cancel(pro, *, actor=None) -> Subscription:
    """Stops at the end of the paid month (or of the trial)."""
    subscription = _locked(pro)
    if not selectors.is_paying(subscription):
        raise errors.NoPayment()
    subscription.cancel_at_period_end = True
    subscription.save(update_fields=["cancel_at_period_end", "updated_at"])
    record("glowpro.cancelled", subscription, actor=actor)
    return subscription


@transaction.atomic
def resume(pro, *, actor=None) -> Subscription:
    subscription = _locked(pro)
    subscription.cancel_at_period_end = False
    subscription.save(update_fields=["cancel_at_period_end", "updated_at"])
    record("glowpro.resumed", subscription, actor=actor)
    return subscription


def may_cancel_payment(payment: Payment, actor) -> bool:
    return True  # an unpaid month can be left: nothing is lost


def on_payment_change(payment: Payment) -> None:
    """Paid: the money goes to the platform at once and a new month starts."""
    if payment.status == PS.HELD:
        payment_services.release(payment, reason="subscription")
        _paid(payment)
    elif payment.status == PS.CANCELLED:
        Subscription.objects.filter(renewal_payment=payment).update(renewal_payment=None)


@transaction.atomic
def _paid(payment: Payment) -> None:
    subscription = (
        Subscription.objects.select_for_update(of=("self",))
        .select_related("pro__user", "next_plan", "plan")
        .filter(pk=payment.source_id)
        .first()
    )
    if subscription is None or SubscriptionPeriod.objects.filter(payment=payment).exists():
        return
    now = timezone.now()
    plan = subscription.next_plan or subscription.plan
    keeps_running = subscription.status == S.ACTIVE and subscription.current_period_end
    start = max(now, subscription.current_period_end) if keeps_running else now
    end = add_month(start)
    subscription.plan = plan
    subscription.status = S.ACTIVE
    subscription.current_period_end = end
    subscription.grace_until = None
    subscription.renewal_payment = None
    subscription.next_plan = None
    subscription.renewal_noticed_at = None
    subscription.save()
    SubscriptionPeriod.objects.create(
        subscription=subscription, plan=plan, starts_at=start, ends_at=end, payment=payment
    )
    _invoice(subscription, payment, plan, start, end)
    record("glowpro.paid", subscription, metadata={"until": end.isoformat()})
    pro = subscription.pro
    transaction.on_commit(
        lambda: notify(
            pro.user, "glowpro.paid", {"plan": plan.name, "until": end.date().isoformat()},
            link=LINK,
        )
    )  # fmt: skip


def _invoice(subscription, payment: Payment, plan: Plan, start, end) -> None:
    from apps.invoicing import services as invoicing

    pro = subscription.pro
    invoicing.issue_once(
        invoicing.platform_issuer(),
        "invoice",
        source_type="glowpro",
        source_id=payment.pk,
        buyer_name=pro.display_name,
        buyer_details=", ".join(filter(None, (pro.address, pro.city))),
        buyer_user=pro.user,
        lines=[
            {
                "label": f"Glow Pro {plan.name} ({start.date():%d/%m/%Y} - {end.date():%d/%m/%Y})",
                "quantity": 1,
                "unit_minor": payment.items_minor,
            }
        ],
        currency=payment.currency,
        paid_with=payment.reference,
    )


# --- What happens by itself (Celery Beat, every hour) -------------------------------------------


def send_renewals(now=None) -> int:
    """A few days before the end: the payment of next month (or the end of the trial)."""
    now = now or timezone.now()
    count = 0
    rows = Subscription.objects.filter(
        status__in=[S.ACTIVE, S.TRIALING],
        cancel_at_period_end=False,
        renewal_noticed_at__isnull=True,
        current_period_end__isnull=False,
    ).select_related("pro__user", "pro__country", "plan")
    for subscription in rows:
        pro = subscription.pro
        days = int(_setting("glowpro.renewal_notice_days", pro, 3))
        if subscription.current_period_end - datetime.timedelta(days=days) > now:
            continue
        with transaction.atomic():
            event = "glowpro.trial_ending"
            if subscription.status == S.ACTIVE:
                _new_payment(subscription, subscription.plan)
                event = "glowpro.renewal_due"
            subscription.renewal_noticed_at = now
            subscription.save(update_fields=["renewal_noticed_at", "updated_at"])
            end = subscription.current_period_end.date().isoformat()
            plan_name = subscription.plan.name
            transaction.on_commit(
                lambda p=pro, e=event, d=end, n=plan_name: notify(
                    p.user, e, {"plan": n, "until": d}, link=LINK
                )
            )
        count += 1
    return count


def end_periods(now=None) -> dict:
    """End of a month not paid: some days of grace, then back to the free plan."""
    now = now or timezone.now()
    counts = {"past_due": 0, "ended": 0}
    for subscription in Subscription.objects.filter(
        status__in=[S.ACTIVE, S.TRIALING], current_period_end__lte=now
    ).select_related("pro__user", "pro__country"):
        pro = subscription.pro
        if subscription.status == S.TRIALING or subscription.cancel_at_period_end:
            downgrade(subscription)
            counts["ended"] += 1
            continue
        days = int(_setting("glowpro.grace_days", pro, 7))
        subscription.status = S.PAST_DUE
        subscription.grace_until = subscription.current_period_end + datetime.timedelta(days=days)
        subscription.save(update_fields=["status", "grace_until", "updated_at"])
        notify(pro.user, "glowpro.past_due", {"days": days}, link=LINK)
        counts["past_due"] += 1
    for subscription in Subscription.objects.filter(
        status=S.PAST_DUE, grace_until__lte=now
    ).select_related("pro__user"):
        downgrade(subscription)
        counts["ended"] += 1
    return counts


@transaction.atomic
def downgrade(subscription: Subscription) -> Subscription:
    """Back to the free plan: data kept; people beyond the free limit are paused."""
    from apps.booking.models import StaffMember
    from apps.booking.services.common import changed

    pro = subscription.pro
    subscription.status = S.ENDED
    subscription.plan = selectors.default_plan()
    subscription.cancel_at_period_end = False
    subscription.grace_until = None
    subscription.renewal_noticed_at = None
    if (
        subscription.renewal_payment_id
        and subscription.renewal_payment.status == PS.PENDING_PAYMENT
    ):
        payment_services.mark_not_paid(subscription.renewal_payment, reason="subscription_ended")
    subscription.renewal_payment = None
    subscription.save()
    pro._glowpro_subscription = subscription
    allowed = selectors.limit(pro, "staff")
    paused = 0
    if allowed is not None:
        extra = StaffMember.objects.filter(pro=pro, is_owner=False, is_active=True).order_by(
            "position", "created_at"
        )[allowed:]
        paused = StaffMember.objects.filter(pk__in=[m.pk for m in extra]).update(is_active=False)
        if paused:
            changed(pro)
    Widget.objects.filter(pro=pro).update(is_active=False)
    record("glowpro.ended", subscription, metadata={"paused": paused})
    transaction.on_commit(lambda: notify(pro.user, "glowpro.ended", {"paused": paused}, link=LINK))
    return subscription


def run_all(now=None) -> dict:
    now = now or timezone.now()
    return {"renewals": send_renewals(now), **end_periods(now)}


# --- White-label widget (Premium) ---------------------------------------------------------------

DOMAIN = re.compile(r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def clean_domain(value: str) -> str:
    """« https://www.Salon.fr/rdv » → « www.salon.fr »."""
    value = (value or "").strip().lower()
    value = value.split("://", 1)[-1].split("/", 1)[0].split(":", 1)[0]
    return value


@transaction.atomic
def save_widget(pro, *, color: str, allowed_domains: list[str], is_active: bool = True) -> Widget:
    selectors.require(pro, Feature.WIDGET)
    domains = sorted({clean_domain(d) for d in allowed_domains if clean_domain(d)})
    if (
        not COLOR.match(color or "")
        or len(domains) > 10
        or not all(DOMAIN.match(d) for d in domains)
    ):
        raise errors.InvalidWidget()
    widget, _ = Widget.objects.get_or_create(pro=pro)
    widget.color, widget.allowed_domains, widget.is_active = color, domains, bool(is_active)
    widget.save()
    record("glowpro.widget_saved", widget, metadata={"domains": domains})
    return widget


def widget_for(slug: str) -> Widget | None:
    """The widget of a published pro, only while she is Premium."""
    widget = (
        Widget.objects.select_related("pro")
        .filter(pro__slug=slug, pro__status="published", is_active=True)
        .first()
    )
    if widget is None or not selectors.has_feature(widget.pro, Feature.WIDGET):
        return None
    return widget
