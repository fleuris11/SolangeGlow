"""The monthly pass: the platform sells it, the money is released at once, nothing is taken
automatically (a reminder with the payment of next month, then it stops)."""

from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from apps.core.audit.services import record
from apps.glowpro.services import add_month
from apps.notifications.services import notify
from apps.payments import services as payment_services
from apps.payments.models import Payment, Purpose

from .. import errors, selectors
from ..models import AcademyPass, PassPeriod
from .common import PASS_SOURCE, require_open, setting

S = AcademyPass.Status
PS = Payment.Status
LINK = "/academie/pass"


def _locked(user) -> AcademyPass:
    country = user.country
    if country is None:
        raise errors.PassNotOffered()
    found, _ = AcademyPass.objects.get_or_create(user=user, defaults={"country": country})
    return (
        AcademyPass.objects.select_for_update(of=("self",))
        .select_related("renewal_payment", "country__default_currency")
        .get(pk=found.pk)
    )


def _new_payment(academy_pass: AcademyPass) -> Payment:
    price = selectors.pass_price(academy_pass.country)
    if price is None:
        raise errors.PassNotOffered()
    payment = payment_services.create_payment(
        academy_pass.user,
        selectors.house_account(academy_pass.country),
        purpose=Purpose.ACADEMY_PASS,
        items_minor=price,
        currency=selectors.currency_of(academy_pass.country),
        description="Solange Glow Académie — pass",
        delivery_mode=Payment.Delivery.SERVICE,
        source_type=PASS_SOURCE,
        source_id=academy_pass.pk,
    )
    academy_pass.renewal_payment = payment
    academy_pass.save(update_fields=["renewal_payment", "updated_at"])
    return payment


@transaction.atomic
def subscribe(user) -> Payment:
    """The payment page of the month (the same one while it is waiting)."""
    if user.country is None:
        raise errors.PassNotOffered()
    require_open(user.country)
    if selectors.pass_price(user.country) is None:
        raise errors.PassNotOffered()
    academy_pass = _locked(user)
    active = academy_pass.status == S.ACTIVE and (
        academy_pass.current_period_end and academy_pass.current_period_end > timezone.now()
    )
    if active and academy_pass.renewal_payment_id is None:
        raise errors.PassActive()
    payment = academy_pass.renewal_payment
    if payment is None or payment.status != PS.PENDING_PAYMENT:
        payment = _new_payment(academy_pass)
    academy_pass.cancel_at_period_end = False
    academy_pass.save(update_fields=["cancel_at_period_end", "updated_at"])
    record("academy.pass_checkout", academy_pass, actor=user)
    return payment_services.start_checkout(payment, buyer=user)


@transaction.atomic
def cancel(user) -> AcademyPass:
    academy_pass = _locked(user)
    if academy_pass.status != S.ACTIVE:
        raise errors.NothingToPay()
    academy_pass.cancel_at_period_end = True
    payment = academy_pass.renewal_payment
    if payment is not None and payment.status == PS.PENDING_PAYMENT:
        payment_services.mark_not_paid(payment, reason="pass_cancelled")
        academy_pass.renewal_payment = None
    academy_pass.save()
    record("academy.pass_cancelled", academy_pass, actor=user)
    return academy_pass


def may_cancel_payment(payment: Payment, actor) -> bool:
    return True


def on_payment_change(payment: Payment) -> None:
    if payment.status == PS.HELD:
        payment_services.release(payment, reason="academy_pass")
        _paid(payment)
    elif payment.status == PS.CANCELLED:
        AcademyPass.objects.filter(renewal_payment=payment).update(renewal_payment=None)


@transaction.atomic
def _paid(payment: Payment) -> None:
    academy_pass = (
        AcademyPass.objects.select_for_update(of=("self",))
        .select_related("user")
        .filter(pk=payment.source_id)
        .first()
    )
    if academy_pass is None or PassPeriod.objects.filter(payment=payment).exists():
        return
    now = timezone.now()
    running = (
        academy_pass.status == S.ACTIVE
        and academy_pass.current_period_end
        and academy_pass.current_period_end > now
    )
    start = academy_pass.current_period_end if running else now
    end = add_month(start)
    academy_pass.status = S.ACTIVE
    academy_pass.current_period_end = end
    academy_pass.renewal_payment = None
    academy_pass.renewal_noticed_at = None
    academy_pass.cancel_at_period_end = False
    academy_pass.save()
    PassPeriod.objects.create(
        academy_pass=academy_pass, starts_at=start, ends_at=end, payment=payment
    )
    _invoice(academy_pass, payment, start, end)
    record("academy.pass_paid", academy_pass, metadata={"until": end.isoformat()})
    user = academy_pass.user
    until = timezone.localdate(end).isoformat()
    transaction.on_commit(
        lambda: notify(user, "academy.pass_paid", {"until": until}, link="/academie")
    )


def _invoice(academy_pass: AcademyPass, payment: Payment, start, end) -> None:
    from apps.invoicing import services as invoicing

    user = academy_pass.user
    invoicing.issue_once(
        invoicing.platform_issuer(),
        "invoice",
        source_type=PASS_SOURCE,
        source_id=payment.pk,
        buyer_name=user.first_name or str(user.phone or user.email or ""),
        buyer_user=user,
        lines=[
            {
                "label": f"Pass Académie ({timezone.localdate(start):%d/%m/%Y} - "
                f"{timezone.localdate(end):%d/%m/%Y})",
                "quantity": 1,
                "unit_minor": payment.items_minor,
            }
        ],
        currency=payment.currency,
        paid_with=payment.reference,
    )


# --- By itself (Celery Beat) --------------------------------------------------------------------


def send_renewals(now=None) -> int:
    """A few days before the end: the payment of next month."""
    now = now or timezone.now()
    count = 0
    rows = AcademyPass.objects.filter(
        status=S.ACTIVE,
        cancel_at_period_end=False,
        renewal_noticed_at__isnull=True,
        current_period_end__isnull=False,
    ).select_related("user", "country")
    for academy_pass in rows:
        days = int(setting("academy.pass_notice_days", academy_pass.country, 3))
        if academy_pass.current_period_end - datetime.timedelta(days=days) > now:
            continue
        if selectors.pass_price(academy_pass.country) is None:
            continue
        with transaction.atomic():
            _new_payment(academy_pass)
            academy_pass.renewal_noticed_at = now
            academy_pass.save(update_fields=["renewal_noticed_at", "updated_at"])
            user = academy_pass.user
            until = timezone.localdate(academy_pass.current_period_end).isoformat()
            transaction.on_commit(
                lambda u=user, d=until: notify(
                    u, "academy.pass_renewal_due", {"until": d}, link=LINK
                )
            )
        count += 1
    return count


def end_periods(now=None) -> int:
    """A month not paid: the pass stops (courses of the pass close until she pays again)."""
    now = now or timezone.now()
    count = 0
    for academy_pass in AcademyPass.objects.filter(
        status=S.ACTIVE, current_period_end__lte=now
    ).select_related("user", "renewal_payment"):
        with transaction.atomic():
            academy_pass.status = S.ENDED
            academy_pass.renewal_noticed_at = None
            academy_pass.save(update_fields=["status", "renewal_noticed_at", "updated_at"])
            user = academy_pass.user
            transaction.on_commit(lambda u=user: notify(u, "academy.pass_ended", {}, link=LINK))
        count += 1
    return count
