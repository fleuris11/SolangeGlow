"""Several payments paid in one go (a cart with several shops): one provider page, one
answer, then each payment goes its own way (its seller, its code, its ledger entries).

The provider's charge is split in the ledger by the payments themselves: each one posts
its own « paid » entry; the provider fee is shared in proportion to the amounts.
"""

from __future__ import annotations

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.audit.services import record

from .. import errors
from ..models import Payment, PaymentGroup
from ..providers import get_provider
from . import payments as payment_services
from .common import S


def create_group(buyer, payments: list[Payment]) -> PaymentGroup:
    """Groups payments of the same client, currency and provider, not paid yet."""
    if not payments:
        raise errors.InvalidPayment()
    first = payments[0]
    for payment in payments:
        if (
            payment.buyer_id != buyer.pk
            or payment.status != S.PENDING_PAYMENT
            or payment.group_id
            or payment.currency != first.currency
            or payment.provider != first.provider
        ):
            raise errors.InvalidPayment()
    values = {
        "buyer": buyer,
        "currency": first.currency,
        "total_minor": sum(p.total_minor for p in payments),
        "provider": first.provider,
        "expires_at": min(p.expires_at for p in payments),
    }
    for _ in range(5):
        try:
            with transaction.atomic():
                group = PaymentGroup.objects.create(
                    reference=payment_services._new_reference(), **values
                )
            break
        except IntegrityError:  # the same reference twice: try another one
            continue
    else:  # pragma: no cover - 32^8 references
        raise errors.InvalidPayment()
    Payment.objects.filter(pk__in=[p.pk for p in payments]).update(group=group)
    for payment in payments:
        payment.group = group
    record("payments.group_created", group, actor=buyer)
    return group


def start_group_checkout(group: PaymentGroup, *, buyer) -> PaymentGroup:
    """The provider's page for the whole amount (created once, reused while valid)."""
    if group.buyer_id != buyer.pk:
        raise errors.PaymentNotFound()
    if group.payments.exclude(status=S.PENDING_PAYMENT).exists():
        raise errors.InvalidTransition()  # paid, or too late: the orders are gone
    if group.checkout_url:
        return group
    provider = get_provider(group.provider)
    checkout = provider.create_checkout(
        group, return_url=f"{settings.SITE_URL}/checkout/done/{group.pk}"
    )
    group.provider_reference = checkout.reference
    group.checkout_url = checkout.url
    group.save(update_fields=["provider_reference", "checkout_url", "updated_at"])
    # Refunds are asked per payment, against the same charge.
    group.payments.update(provider_reference=checkout.reference)
    return group


@transaction.atomic
def mark_group_paid(
    group: PaymentGroup, *, amount_minor, currency: str, fee_minor: int = 0, key: str
) -> PaymentGroup:
    group = PaymentGroup.objects.select_for_update().get(pk=group.pk)
    if group.paid_at:
        return group  # the same news twice
    if amount_minor != group.total_minor or currency.upper() != group.currency:
        raise errors.InvalidPayment(
            details={"expected": group.total_minor, "received": amount_minor}
        )
    members = list(group.payments.order_by("created_at", "pk"))
    shared = 0
    for index, payment in enumerate(members):
        if index == len(members) - 1:
            fee = fee_minor - shared
        else:
            fee = fee_minor * payment.total_minor // group.total_minor
        shared += fee
        payment_services.mark_paid(
            payment,
            amount_minor=payment.total_minor,
            currency=group.currency,
            fee_minor=fee,
            key=f"{key}:{payment.pk}",
        )
    group.paid_at = timezone.now()
    group.save(update_fields=["paid_at", "updated_at"])
    return group


@transaction.atomic
def pay_group_from_gift(group: PaymentGroup, *, key: str) -> PaymentGroup:
    """A whole cart paid with the money of a gift (ADR-014), in one go."""
    group = PaymentGroup.objects.select_for_update().get(pk=group.pk)
    members = list(group.payments.order_by("created_at", "pk"))
    if (
        group.paid_at
        or group.currency != "XOF"
        or any(p.status != S.PENDING_PAYMENT for p in members)
    ):
        raise errors.InvalidTransition()
    group.provider = payment_services.GIFT
    group.provider_reference = key[:120]
    group.checkout_url = ""
    group.save(update_fields=["provider", "provider_reference", "checkout_url", "updated_at"])
    Payment.objects.filter(pk__in=[p.pk for p in members]).update(
        provider=payment_services.GIFT, provider_reference=key[:120], checkout_url=""
    )
    for payment in members:
        payment_services.mark_paid(
            payment,
            amount_minor=payment.total_minor,
            currency=group.currency,
            key=f"{key}:{payment.pk}",
        )
    group.paid_at = timezone.now()
    group.save(update_fields=["paid_at", "updated_at"])
    return group


def mark_group_not_paid(group: PaymentGroup, *, reason: str) -> PaymentGroup:
    for payment in group.payments.all():
        payment_services.mark_not_paid(payment, reason=reason)
    return group


def group_status(group: PaymentGroup) -> str:
    """« paid » once the provider answered, « cancelled » when every order is gone."""
    if group.paid_at:
        return "paid"
    statuses = set(group.payments.values_list("status", flat=True))
    if statuses and statuses <= {S.CANCELLED}:
        return "cancelled"
    return "pending"
