"""A secure payment from the order to the money of the seller (or back to the client).

Ledger entries of each step (example: items 10 000 + delivery 1 000, buyer protection 330,
commission 500), see ADR-007:
- paid:     Dr provider cash 11 330 / Cr seller pending 11 000, Cr fees pending 330
- released: Dr seller pending 11 000, Dr fees pending 330 /
            Cr seller available 10 500, Cr commissions 500, Cr buyer protection 330
- refunded: Dr seller pending 11 000, Dr fees pending 330 / Cr refunds in progress 11 330
- partial (4 000 back): Dr seller pending 11 000, Dr fees pending 330 / Cr refunds in
            progress 4 000, Cr seller available 6 700, Cr commissions 300, Cr protection 330
"""

from __future__ import annotations

import datetime
import hashlib
import hmac
import secrets

from django.conf import settings
from django.core import signing
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core import crypto
from apps.core.audit.services import record
from apps.core.media.models import MediaAsset
from apps.core.money import Money, UnknownCurrencyError
from apps.core.selectors import get_setting
from apps.notifications.services import notify

from .. import errors, ledger, pricing
from ..ledger import credit, debit
from ..models import LedgerAccount, Payment, PricingRule, Purpose, Refund
from ..providers import ProviderNotConfigured, get_provider, provider_for
from . import common
from .common import S, locked, move

Kind = LedgerAccount.Kind
GIFT = "gift"  # the internal provider of the gifts (providers/gift.py)
COURIER_SALT = "payments.courier"


def money(amount_minor: int, currency: str, user=None) -> str:
    language = getattr(user, "preferred_language", "") or "fr"
    return Money(amount_minor, currency).format(language)


def _country_of(user) -> str:
    """The seller's country (her showcase, else her account): it chooses rules and provider."""
    try:
        pro = user.pro_profile
    except ObjectDoesNotExist:
        pro = None
    if pro is not None and pro.country_id:
        return pro.country.code
    return user.country.code if user.country_id else ""


def _new_reference() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "SG-" + "".join(secrets.choice(alphabet) for _ in range(8))


def ship_days(payment: Payment) -> int:
    """Days the seller has to ship: the setting, plus the preparation of made-to-order items."""
    days = int(get_setting("escrow.ship_deadline_days", country=payment.country or None, default=3))
    return days + payment.prep_days


# --- Creation and checkout -----------------------------------------------------------------------


def buyer_fee(
    seller,
    *,
    purpose: str,
    items_minor: int,
    delivery_minor: int,
    currency: str,
    category: str = "",
) -> int:
    """The buyer protection a payment would carry (shown before ordering)."""
    return pricing.charge(
        PricingRule.Kind.BUYER_PROTECTION,
        items_minor + delivery_minor,
        currency=currency.upper(),
        country=_country_of(seller),
        category=category,
        seller=seller,
        purpose=purpose,
    ).amount_minor


def create_payment(
    buyer,
    seller,
    *,
    purpose: str,
    items_minor: int,
    currency: str,
    description: str,
    delivery_minor: int = 0,
    delivery_mode: str = Payment.Delivery.SELLER,
    category: str = "",
    source_type: str = "",
    source_id=None,
    service_at=None,
    prep_days: int = 0,
    with_buyer_fee: bool = True,
) -> Payment:
    """A payment waiting for the client to pay: amounts, fees and rules fixed now.

    `with_buyer_fee=False`: no buyer protection (a gift from abroad already paid its own fee).
    """
    try:
        Money(0, currency)
    except (UnknownCurrencyError, TypeError) as exc:
        raise errors.InvalidPayment() from exc
    if (
        buyer.pk == seller.pk
        or type(items_minor) is not int
        or type(delivery_minor) is not int
        or items_minor <= 0
        or delivery_minor < 0
    ):
        raise errors.InvalidPayment()
    currency = currency.upper()
    country = _country_of(seller)
    criteria = {
        "currency": currency,
        "country": country,
        "category": category,
        "seller": seller,
        "purpose": purpose,
    }
    commission = pricing.charge(PricingRule.Kind.COMMISSION, items_minor, **criteria)
    protection = (
        pricing.charge(PricingRule.Kind.BUYER_PROTECTION, items_minor + delivery_minor, **criteria)
        if with_buyer_fee
        else pricing.Charge(None, 0)
    )
    try:
        provider = provider_for(country)
    except ProviderNotConfigured as exc:
        raise errors.PaymentsUnavailable() from exc
    minutes = int(get_setting("escrow.payment_timeout_minutes", country=country, default=30))
    values = {
        "buyer": buyer,
        "seller": seller,
        "purpose": purpose,
        "description": description[:200],
        "country": country,
        "category": category,
        "currency": currency,
        "items_minor": items_minor,
        "delivery_minor": delivery_minor,
        "commission_minor": commission.amount_minor,
        "commission_rule": commission.rule,
        "buyer_fee_minor": protection.amount_minor,
        "buyer_fee_rule": protection.rule,
        "total_minor": items_minor + delivery_minor + protection.amount_minor,
        "provider": provider.name,
        "delivery_mode": delivery_mode,
        "source_type": source_type,
        "source_id": source_id,
        "service_at": service_at,
        "prep_days": max(int(prep_days), 0),
        "expires_at": timezone.now() + datetime.timedelta(minutes=minutes),
    }
    for _ in range(5):
        try:
            with transaction.atomic():
                payment = Payment.objects.create(reference=_new_reference(), **values)
            break
        except IntegrityError:  # the same reference twice: try another one
            continue
    else:  # pragma: no cover - 32^8 references
        raise errors.InvalidPayment()
    record("payments.created", payment, actor=buyer)
    return payment


def start_checkout(payment: Payment, *, buyer) -> Payment:
    """The payment page of the provider (created once, reused while it is valid)."""
    if payment.buyer_id != buyer.pk:
        raise errors.PaymentNotFound()
    if payment.status != S.PENDING_PAYMENT or payment.group_id:
        raise errors.InvalidTransition()  # a grouped payment is paid with its group
    if payment.checkout_url:
        return payment
    provider = get_provider(payment.provider)
    checkout = provider.create_checkout(
        payment, return_url=f"{settings.SITE_URL}/payments/{payment.pk}"
    )
    payment.provider_reference = checkout.reference
    payment.checkout_url = checkout.url
    payment.save(update_fields=["provider_reference", "checkout_url", "updated_at"])
    return payment


# --- Paid, not paid ------------------------------------------------------------------------------


def _escrow_lines(payment: Payment) -> tuple:
    currency = payment.currency
    return (
        ledger.account(Kind.SELLER_PENDING, currency, owner=payment.seller),
        ledger.account(Kind.FEES_PENDING, currency),
    )


@transaction.atomic
def mark_paid(
    payment: Payment,
    *,
    amount_minor,
    currency: str,
    fee_minor: int = 0,
    key: str,
    tell_buyer: bool = True,
):
    """The provider confirmed the payment: money held, receipt code sent.

    `tell_buyer=False`: the module tells the client itself (a gift: the code is on its page).
    """
    payment = locked(payment)
    if payment.status not in (S.PENDING_PAYMENT, S.CANCELLED):
        return payment  # already counted (the same news twice)
    if amount_minor != payment.total_minor or currency.upper() != payment.currency:
        raise errors.InvalidPayment(
            details={"expected": payment.total_minor, "received": amount_minor}
        )
    currency = payment.currency
    cash = ledger.account(Kind.PROVIDER_CASH, currency, provider=payment.provider)
    pending, fees = _escrow_lines(payment)
    ledger.post(
        "payment.held",
        f"payment:{payment.pk}:held",
        [
            debit(cash, payment.total_minor),
            credit(pending, payment.seller_gross_minor),
            credit(fees, payment.buyer_fee_minor),
        ],
        payment=payment,
        description=payment.reference,
    )
    if fee_minor:
        ledger.post(
            "payment.provider_fee",
            f"payment:{payment.pk}:provider_fee",
            [
                debit(
                    ledger.account(Kind.PROVIDER_FEES, currency, provider=payment.provider),
                    fee_minor,
                ),
                credit(cash, fee_minor),
            ],
            payment=payment,
        )
    if payment.status == S.CANCELLED:
        # Paid too late: the order is gone, the money goes back at once.
        refund_full(payment, actor=None, reason="late_payment", _locked=True)
        return payment
    move(payment, S.HELD, reason="paid")
    code = _new_receipt_code(payment)
    payment.save(update_fields=["receipt_code_hash", "receipt_code_secret", "updated_at"])
    days = ship_days(payment)
    total = money(payment.total_minor, currency, payment.buyer)
    # A gift from abroad has no receipt code to give: its own module tells the giver.
    tell_buyer = tell_buyer and payment.purpose != Purpose.GIFT
    transaction.on_commit(
        lambda: (
            tell_buyer
            and notify(
                payment.buyer,
                "payments.paid",
                {"reference": payment.reference, "amount": total},
                link=f"/payments/{payment.pk}",
                secret={"code": code},
            ),
            notify(
                payment.seller,
                "payments.new_sale",
                {
                    "reference": payment.reference,
                    "amount": money(payment.seller_gross_minor, currency, payment.seller),
                    "days": days,
                },
                link=f"/payments/{payment.pk}",
            ),
        )
    )
    return payment


@transaction.atomic
def pay_from_gift(payment: Payment, *, key: str, tell_buyer: bool = True) -> Payment:
    """Paid with the money of a gift (ADR-014): no provider page, held at once."""
    payment = locked(payment)
    if payment.status != S.PENDING_PAYMENT or payment.group_id or payment.currency != "XOF":
        raise errors.InvalidTransition()
    payment.provider = GIFT
    payment.provider_reference = key[:120]
    payment.checkout_url = ""
    payment.save(update_fields=["provider", "provider_reference", "checkout_url", "updated_at"])
    return mark_paid(
        payment,
        amount_minor=payment.total_minor,
        currency=payment.currency,
        key=key,
        tell_buyer=tell_buyer,
    )


@transaction.atomic
def mark_not_paid(payment: Payment, *, reason: str) -> Payment:
    """Failed, given up or too late: nothing was paid, nothing moves in the ledger."""
    payment = locked(payment)
    if payment.status != S.PENDING_PAYMENT:
        return payment
    move(payment, S.CANCELLED, reason=reason)
    return payment


# --- Delivery ------------------------------------------------------------------------------------


def _seller_only(payment: Payment, actor) -> None:
    if actor is None or payment.seller_id != actor.pk:
        raise errors.PaymentNotFound()


@transaction.atomic
def ship(
    payment: Payment,
    *,
    actor,
    carrier: str = "",
    tracking_number: str = "",
    expected_delivery_at=None,
) -> Payment:
    payment = locked(payment)
    _seller_only(payment, actor)
    if payment.delivery_mode == Payment.Delivery.SERVICE:
        raise errors.InvalidTransition()
    days = int(get_setting("escrow.expected_delivery_days", country=payment.country, default=5))
    payment.carrier = carrier.strip()[:80]
    payment.tracking_number = tracking_number.strip()[:80]
    payment.expected_delivery_at = expected_delivery_at or (
        timezone.now() + datetime.timedelta(days=days)
    )
    payment.save(update_fields=["carrier", "tracking_number", "expected_delivery_at", "updated_at"])
    move(payment, S.SHIPPED, actor=actor)
    pickup = payment.delivery_mode == Payment.Delivery.PICKUP
    transaction.on_commit(
        lambda: notify(
            payment.buyer,
            "payments.ready_for_pickup" if pickup else "payments.shipped",
            {"reference": payment.reference, "carrier": payment.carrier},
            link=f"/payments/{payment.pk}",
        )
    )
    return payment


@transaction.atomic
def mark_delivered(payment: Payment, *, actor, proof_media_id) -> Payment:
    """The seller says it was delivered (a picture is required): reminders, then release."""
    payment = locked(payment)
    _seller_only(payment, actor)
    if payment.status != S.SHIPPED:
        raise errors.InvalidTransition()
    proof = MediaAsset.objects.filter(
        pk=proof_media_id, owner=actor, purpose="delivery_proof"
    ).first()
    if proof is None or not proof.is_ready:
        raise errors.ProofNeeded()
    payment.delivered_at = timezone.now()
    payment.delivery_proof = proof
    payment.save(update_fields=["delivered_at", "delivery_proof", "updated_at"])
    record("payments.delivered", payment, actor=actor)
    transaction.on_commit(
        lambda: notify(
            payment.buyer,
            "payments.delivered",
            {"reference": payment.reference},
            link=f"/payments/{payment.pk}",
        )
    )
    return payment


# --- Receipt code --------------------------------------------------------------------------------


def _hash_code(payment: Payment, code: str) -> str:
    message = f"receipt|{payment.pk}|{code}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def _new_receipt_code(payment: Payment) -> str:
    code = f"{secrets.randbelow(1_000_000):06d}"
    payment.receipt_code_hash = _hash_code(payment, code)
    payment.receipt_code_secret = crypto.encrypt(code)
    payment.receipt_code_attempts = 0
    return code


def receipt_code_for(payment: Payment, user) -> str | None:
    """Shown to the client only, while the order waits for its delivery (a gift from
    abroad has none: nothing is handed over against it)."""
    if payment.buyer_id != user.pk or payment.purpose == Purpose.GIFT:
        return None
    return receipt_code_of(payment)


def receipt_code_of(payment: Payment) -> str | None:
    """The code while the order waits for its delivery (the page of a gift shows it)."""
    if payment.status not in (S.HELD, S.SHIPPED) or not payment.receipt_code_secret:
        return None
    return crypto.decrypt(payment.receipt_code_secret)


def _max_attempts(payment: Payment) -> int:
    return int(get_setting("escrow.receipt_code_max_attempts", country=payment.country, default=5))


def confirm_receipt(payment: Payment, code: str, *, actor=None) -> Payment:
    """The seller (or the courier, without account) types the code: money to the seller."""
    with transaction.atomic():
        payment = locked(payment)
        if actor is not None:
            _seller_only(payment, actor)
        if payment.status not in (S.HELD, S.SHIPPED):
            raise errors.InvalidTransition()
        allowed = _max_attempts(payment)
        if payment.receipt_code_attempts >= allowed:
            raise errors.CodeLocked()
        right = hmac.compare_digest(
            _hash_code(payment, (code or "").strip()), payment.receipt_code_hash
        )
        if right:
            return release(payment, actor=actor, reason="receipt_code", _locked=True)
        payment.receipt_code_attempts += 1
        payment.save(update_fields=["receipt_code_attempts", "updated_at"])
        left = allowed - payment.receipt_code_attempts
        if left == 0:
            transaction.on_commit(
                lambda: notify(
                    payment.buyer,
                    "payments.code_locked",
                    {"reference": payment.reference},
                    link=f"/payments/{payment.pk}",
                )
            )
    # Outside the transaction: the wrong attempt stays counted.
    raise errors.WrongCode(details={"left": left})


@transaction.atomic
def renew_receipt_code(payment: Payment, *, buyer) -> Payment:
    payment = locked(payment)
    if payment.buyer_id != buyer.pk:
        raise errors.PaymentNotFound()
    if payment.status not in (S.HELD, S.SHIPPED):
        raise errors.InvalidTransition()
    limit = int(get_setting("escrow.receipt_code_renewals_max", country=payment.country, default=3))
    if payment.receipt_code_renewals >= limit:
        raise errors.TooManyNewCodes()
    code = _new_receipt_code(payment)
    payment.receipt_code_renewals += 1
    payment.save(
        update_fields=[
            "receipt_code_hash",
            "receipt_code_secret",
            "receipt_code_attempts",
            "receipt_code_renewals",
            "updated_at",
        ]
    )
    record("payments.code_renewed", payment, actor=buyer)
    transaction.on_commit(
        lambda: notify(
            payment.buyer,
            "payments.new_code",
            {"reference": payment.reference},
            link=f"/payments/{payment.pk}",
            secret={"code": code},
        )
    )
    return payment


def courier_token(payment: Payment, *, seller) -> str:
    """A link for the courier: type the code without an account (expires)."""
    _seller_only(payment, seller)
    if payment.status not in (S.HELD, S.SHIPPED):
        raise errors.InvalidTransition()
    return signing.dumps({"p": str(payment.pk)}, salt=COURIER_SALT)


def payment_for_courier(token: str) -> Payment:
    hours = int(get_setting("escrow.courier_link_hours", default=72))
    try:
        data = signing.loads(token, salt=COURIER_SALT, max_age=hours * 3600)
    except signing.BadSignature as exc:
        raise errors.InvalidCourierLink() from exc
    payment = Payment.objects.filter(pk=data.get("p")).first()
    if payment is None or payment.status not in (S.HELD, S.SHIPPED):
        raise errors.InvalidCourierLink()
    return payment


# --- Outcomes ------------------------------------------------------------------------------------


def _release_lines(payment: Payment, *, kept_gross: int, commission: int) -> list:
    currency = payment.currency
    pending, fees = _escrow_lines(payment)
    lines = [
        debit(pending, payment.seller_gross_minor),
        credit(
            ledger.account(Kind.SELLER_AVAILABLE, currency, owner=payment.seller),
            kept_gross - commission,
        ),
        credit(ledger.account(Kind.COMMISSION_REVENUE, currency), commission),
        debit(fees, payment.buyer_fee_minor),
        credit(ledger.account(Kind.FEE_REVENUE, currency), payment.buyer_fee_minor),
    ]
    return lines


def release(payment: Payment, *, actor=None, reason: str, _locked: bool = False) -> Payment:
    """Money to the seller (minus the commission), protection fee to the platform."""
    with transaction.atomic():
        if not _locked:
            payment = locked(payment)
        move(payment, S.RELEASED, actor=actor, reason=reason)
        ledger.post(
            "payment.released",
            f"payment:{payment.pk}:released",
            _release_lines(
                payment, kept_gross=payment.seller_gross_minor, commission=payment.commission_minor
            ),
            payment=payment,
            actor=actor,
            description=reason,
        )
        net = payment.seller_gross_minor - payment.commission_minor
        transaction.on_commit(
            lambda: (
                notify(
                    payment.seller,
                    "payments.released",
                    {
                        "reference": payment.reference,
                        "amount": money(net, payment.currency, payment.seller),
                    },
                    link="/pro/wallet",
                ),
                payment.purpose != Purpose.GIFT
                and notify(
                    payment.buyer,
                    "payments.completed",
                    {"reference": payment.reference},
                    link=f"/payments/{payment.pk}",
                ),
            )
        )
    return payment


def refund_full(payment: Payment, *, actor=None, reason: str, _locked: bool = False) -> Payment:
    """Everything back to the client, protection fee included."""
    from ..tasks import run_refund

    with transaction.atomic():
        if not _locked:
            payment = locked(payment)
        move(payment, S.REFUNDED, actor=actor, reason=reason)
        pending, fees = _escrow_lines(payment)
        refund = Refund.objects.create(
            payment=payment,
            amount_minor=payment.total_minor,
            currency=payment.currency,
            reason=reason[:40],
        )
        ledger.post(
            "payment.refunded",
            f"payment:{payment.pk}:refunded",
            [
                debit(pending, payment.seller_gross_minor),
                debit(fees, payment.buyer_fee_minor),
                credit(
                    ledger.account(Kind.REFUNDS_IN_TRANSIT, payment.currency), payment.total_minor
                ),
            ],
            payment=payment,
            refund=refund,
            actor=actor,
            description=reason,
        )
        payment.refunded_minor = payment.total_minor
        payment.save(update_fields=["refunded_minor", "updated_at"])
        amount = money(payment.total_minor, payment.currency, payment.buyer)
        transaction.on_commit(
            lambda: (
                run_refund.delay(str(refund.pk)),
                notify(
                    payment.buyer,
                    "payments.refunded",
                    {"reference": payment.reference, "amount": amount},
                    link=f"/payments/{payment.pk}",
                ),
                notify(
                    payment.seller,
                    "payments.sale_cancelled",
                    {"reference": payment.reference},
                    link=f"/payments/{payment.pk}",
                ),
            )
        )
    return payment


def refund_partial(payment: Payment, amount_minor: int, *, actor, reason: str) -> Payment:
    """Part of the seller's amount back to the client (the protection fee stays due).

    The commission is taken on the items the seller keeps, in proportion.
    """
    from ..tasks import run_refund

    with transaction.atomic():
        payment = locked(payment)
        gross = payment.seller_gross_minor
        if type(amount_minor) is not int or not 0 < amount_minor < gross:
            raise errors.InvalidRefundAmount(details={"total": money(gross, payment.currency)})
        move(payment, S.PARTIALLY_REFUNDED, actor=actor, reason=reason)
        kept_items = max(payment.items_minor - amount_minor, 0)
        commission = (payment.commission_minor * kept_items * 2 + payment.items_minor) // (
            2 * payment.items_minor
        )
        refund = Refund.objects.create(
            payment=payment,
            amount_minor=amount_minor,
            currency=payment.currency,
            reason=reason[:40],
        )
        lines = _release_lines(payment, kept_gross=gross - amount_minor, commission=commission)
        lines.append(
            credit(ledger.account(Kind.REFUNDS_IN_TRANSIT, payment.currency), amount_minor)
        )
        ledger.post(
            "payment.partially_refunded",
            f"payment:{payment.pk}:partially_refunded",
            lines,
            payment=payment,
            refund=refund,
            actor=actor,
            description=reason,
        )
        payment.refunded_minor = amount_minor
        payment.commission_minor = commission
        payment.save(update_fields=["refunded_minor", "commission_minor", "updated_at"])
        transaction.on_commit(
            lambda: (
                run_refund.delay(str(refund.pk)),
                notify(
                    payment.buyer,
                    "payments.refunded",
                    {
                        "reference": payment.reference,
                        "amount": money(amount_minor, payment.currency, payment.buyer),
                    },
                    link=f"/payments/{payment.pk}",
                ),
                notify(
                    payment.seller,
                    "payments.released",
                    {
                        "reference": payment.reference,
                        "amount": money(
                            gross - amount_minor - commission, payment.currency, payment.seller
                        ),
                    },
                    link="/pro/wallet",
                ),
            )
        )
    return payment


def cancel(payment: Payment, *, actor) -> Payment:
    """Before shipping, the client or the seller cancels: everything back to the client."""
    with transaction.atomic():
        payment = locked(payment)
        if actor is None or actor.pk not in (payment.buyer_id, payment.seller_id):
            raise errors.PaymentNotFound()
        if payment.status != S.HELD:
            raise errors.InvalidTransition()
        if not common.may_cancel(payment, actor):
            raise errors.CancelNotAllowed()
        reason = "buyer_cancelled" if actor.pk == payment.buyer_id else "seller_cancelled"
        return refund_full(payment, actor=actor, reason=reason, _locked=True)


__all__ = [
    "buyer_fee",
    "cancel",
    "common",
    "confirm_receipt",
    "courier_token",
    "create_payment",
    "mark_delivered",
    "mark_not_paid",
    "mark_paid",
    "pay_from_gift",
    "payment_for_courier",
    "receipt_code_for",
    "receipt_code_of",
    "refund_full",
    "refund_partial",
    "release",
    "renew_receipt_code",
    "ship",
    "ship_days",
    "start_checkout",
]
