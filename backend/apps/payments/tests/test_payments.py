"""Every move of a secure payment, its ledger entries and its refusals."""

import itertools

import pytest
from django.core import signing
from django.test import override_settings

from apps.core.tests.factories import PlatformSettingFactory
from apps.messaging.tests.factories import adult
from apps.notifications.models import Notification, NotificationDelivery
from apps.payments import errors, ledger, services
from apps.payments.models import JournalEntry, Payment, Refund
from apps.payments.services import common
from apps.payments.services.common import ALLOWED, S

from .factories import balances, code_of, commission, paid, payment, picture, seller, shipped

pytestmark = pytest.mark.django_db


# --- Creation ------------------------------------------------------------------------------------


def test_creation_fixes_the_amounts_and_rules():
    commission(500)
    p = payment()
    assert (p.items_minor, p.delivery_minor, p.buyer_fee_minor) == (10_000, 1_000, 330)
    assert p.commission_minor == 500 and p.total_minor == 11_330
    assert p.status == S.PENDING_PAYMENT and p.provider == "fake" and p.country == "BJ"
    assert p.reference.startswith("SG-") and p.expires_at is not None
    assert str(p) == p.reference and p.seller_gross_minor == 11_000


@pytest.mark.parametrize(
    "values",
    [
        {"items_minor": 0},
        {"items_minor": 100.5},
        {"delivery_minor": -1},
        {"delivery_minor": 2.0},
        {"currency": "ABC"},
    ],
)
def test_invalid_amounts_are_refused(values):
    with pytest.raises(errors.InvalidPayment):
        payment(**values)


def test_nobody_buys_from_herself():
    aicha = seller()
    with pytest.raises(errors.InvalidPayment):
        payment(buyer=aicha, sold_by=aicha)


@override_settings(PAYMENTS_FAKE_ENABLED=False)
def test_no_payment_where_no_provider_is_configured():
    with pytest.raises(errors.PaymentsUnavailable):
        payment()


def test_a_seller_without_showcase_uses_her_account_country():
    p = payment(sold_by=adult("Inès"))
    assert p.country == "BJ"


def test_checkout_page_of_the_test_provider():
    p = payment()
    services.start_checkout(p, buyer=p.buyer)
    assert p.checkout_url.endswith(f"/pay/test/{p.pk}") and p.provider_reference
    url = p.checkout_url
    assert services.start_checkout(p, buyer=p.buyer).checkout_url == url
    with pytest.raises(errors.PaymentNotFound):
        services.start_checkout(p, buyer=p.seller)
    paid(p)
    with pytest.raises(errors.InvalidTransition):
        services.start_checkout(p, buyer=p.buyer)


# --- Paid ----------------------------------------------------------------------------------------


def test_paid_money_is_held_and_the_code_is_sent_privately():
    commission(500)
    p = paid()
    assert p.status == S.HELD and p.paid_at is not None
    assert balances(p) | {} == {
        "cash": 11_330,
        "seller_pending": 11_000,
        "fees_pending": 330,
        "seller_available": 0,
        "commissions": 0,
        "protection": 0,
        "refunds": 0,
        "payouts": 0,
        "fees": 0,
    }
    code = code_of(p)
    assert len(code) == 6 and code.isdigit() and code not in p.receipt_code_hash
    # The code went by SMS / WhatsApp, never stored readable.
    alert = Notification.objects.get(user=p.buyer, event_key="payments.paid")
    assert code not in alert.body and code not in str(alert.data)
    for delivery in NotificationDelivery.objects.filter(notification=alert):
        assert code not in delivery.body
    assert Notification.objects.filter(user=p.seller, event_key="payments.new_sale").exists()
    assert ledger.is_balanced()


def test_the_same_news_twice_counts_once():
    p = paid()
    services.mark_paid(p, amount_minor=p.total_minor, currency="XOF", key="again")
    assert JournalEntry.objects.filter(payment=p).count() == 1


@pytest.mark.parametrize(("amount", "currency"), [(11_329, "XOF"), (11_330, "EUR")])
def test_a_wrong_amount_or_currency_is_refused(amount, currency):
    p = payment()
    with pytest.raises(errors.InvalidPayment):
        services.mark_paid(p, amount_minor=amount, currency=currency, key="k")
    p.refresh_from_db()
    assert p.status == S.PENDING_PAYMENT and not JournalEntry.objects.exists()


def test_provider_fees_are_an_expense():
    p = payment()
    services.mark_paid(p, amount_minor=11_330, currency="XOF", fee_minor=170, key="k")
    b = balances(p)
    assert b["cash"] == 11_160 and b["fees"] == 170


def test_failed_or_given_up_payments_end_without_money():
    p = payment()
    services.mark_not_paid(p, reason="abandoned")
    p.refresh_from_db()
    assert p.status == S.CANCELLED and p.end_reason == "abandoned"
    assert services.mark_not_paid(p, reason="failed").status == S.CANCELLED
    assert not JournalEntry.objects.exists()


def test_a_payment_confirmed_too_late_is_refunded_at_once():
    p = payment()
    services.mark_not_paid(p, reason="expired")
    services.mark_paid(p, amount_minor=11_330, currency="XOF", key="late")
    p.refresh_from_db()
    assert p.status == S.REFUNDED and p.end_reason == "late_payment"
    b = balances(p)
    # Refund sent by the test provider and confirmed: everything back to zero.
    assert b["cash"] == 0 and b["seller_pending"] == 0 and b["refunds"] == 0
    assert Refund.objects.get(payment=p).status == Refund.Status.SUCCEEDED


# --- Delivery ------------------------------------------------------------------------------------


def test_only_the_seller_ships_and_a_date_is_expected():
    p = paid()
    with pytest.raises(errors.PaymentNotFound):
        services.ship(p, actor=p.buyer)
    services.ship(p, actor=p.seller, carrier=" Gozem ", tracking_number="GZ-9")
    p.refresh_from_db()
    assert p.status == S.SHIPPED and p.carrier == "Gozem" and p.expected_delivery_at
    with pytest.raises(errors.InvalidTransition):
        services.ship(p, actor=p.seller)
    assert Notification.objects.filter(user=p.buyer, event_key="payments.shipped").exists()


def test_a_service_is_not_shipped():
    p = paid(delivery_mode=Payment.Delivery.SERVICE, delivery_minor=0)
    with pytest.raises(errors.InvalidTransition):
        services.ship(p, actor=p.seller)


def test_delivered_needs_a_picture_of_the_seller():
    p = shipped()
    with pytest.raises(errors.ProofNeeded):
        services.mark_delivered(p, actor=p.seller, proof_media_id=None)
    with pytest.raises(errors.ProofNeeded):
        services.mark_delivered(p, actor=p.seller, proof_media_id=picture(p.buyer).pk)
    with pytest.raises(errors.ProofNeeded):
        services.mark_delivered(
            p, actor=p.seller, proof_media_id=picture(p.seller, status="processing").pk
        )
    services.mark_delivered(p, actor=p.seller, proof_media_id=picture(p.seller).pk)
    p.refresh_from_db()
    assert p.delivered_at is not None and p.status == S.SHIPPED
    assert Notification.objects.filter(user=p.buyer, event_key="payments.delivered").exists()
    held = paid()
    with pytest.raises(errors.InvalidTransition):
        services.mark_delivered(held, actor=held.seller, proof_media_id=picture(held.seller).pk)


# --- Receipt code --------------------------------------------------------------------------------


def test_the_right_code_pays_the_seller_minus_the_commission():
    commission(500)
    p = shipped()
    services.confirm_receipt(p, code_of(p), actor=p.seller)
    p.refresh_from_db()
    assert p.status == S.RELEASED and p.end_reason == "receipt_code"
    b = balances(p)
    assert b["seller_pending"] == 0 and b["fees_pending"] == 0
    assert b["seller_available"] == 10_500 and b["commissions"] == 500 and b["protection"] == 330
    # Cash left at the provider is exactly the platform's revenue once the seller is paid.
    assert b["cash"] - b["seller_available"] == b["commissions"] + b["protection"]
    assert services.receipt_code_for(p, p.buyer) is None
    assert Notification.objects.filter(user=p.seller, event_key="payments.released").exists()
    assert ledger.is_balanced()


def test_wrong_codes_are_counted_then_locked():
    PlatformSettingFactory(key="escrow.receipt_code_max_attempts", value="2")
    p = paid()
    with pytest.raises(errors.WrongCode) as first:
        services.confirm_receipt(p, "000000", actor=p.seller)
    assert first.value.details == {"left": 1}
    p.refresh_from_db()
    assert p.receipt_code_attempts == 1
    with pytest.raises(errors.WrongCode):
        services.confirm_receipt(p, "111111", actor=p.seller)
    assert Notification.objects.filter(user=p.buyer, event_key="payments.code_locked").exists()
    with pytest.raises(errors.CodeLocked):
        services.confirm_receipt(p, code_of(p), actor=p.seller)

    services.renew_receipt_code(p, buyer=p.buyer)
    p.refresh_from_db()
    assert p.receipt_code_attempts == 0
    services.confirm_receipt(p, code_of(p), actor=p.seller)
    assert Payment.objects.get(pk=p.pk).status == S.RELEASED


def test_the_code_is_not_for_others_nor_at_any_stage():
    p = paid()
    with pytest.raises(errors.PaymentNotFound):
        services.confirm_receipt(p, code_of(p), actor=p.buyer)
    assert services.receipt_code_for(p, p.seller) is None
    pending = payment()
    with pytest.raises(errors.InvalidTransition):
        services.confirm_receipt(pending, "123456")


def test_new_codes_are_limited():
    PlatformSettingFactory(key="escrow.receipt_code_renewals_max", value="1")
    p = paid()
    old = code_of(p)
    services.renew_receipt_code(p, buyer=p.buyer)
    p.refresh_from_db()
    assert code_of(p) != old or len(code_of(p)) == 6
    assert Notification.objects.filter(user=p.buyer, event_key="payments.new_code").exists()
    with pytest.raises(errors.TooManyNewCodes):
        services.renew_receipt_code(p, buyer=p.buyer)
    with pytest.raises(errors.PaymentNotFound):
        services.renew_receipt_code(p, buyer=p.seller)


def test_the_new_code_belongs_to_the_buyer():
    p = payment()
    with pytest.raises(errors.InvalidTransition):
        services.renew_receipt_code(p, buyer=p.buyer)


def test_courier_link():
    p = paid()
    token = services.courier_token(p, seller=p.seller)
    assert services.payment_for_courier(token) == p
    services.confirm_receipt(p, code_of(p))  # the courier has no account
    with pytest.raises(errors.InvalidCourierLink):
        services.payment_for_courier(token)  # closed now
    with pytest.raises(errors.InvalidCourierLink):
        services.payment_for_courier("forged")
    with pytest.raises(errors.InvalidCourierLink):
        services.payment_for_courier(signing.dumps({"p": "x"}, salt="other"))
    p.refresh_from_db()
    with pytest.raises(errors.InvalidTransition):
        services.courier_token(p, seller=p.seller)
    with pytest.raises(errors.PaymentNotFound):
        services.courier_token(paid(), seller=p.buyer)


def test_courier_link_expires():
    PlatformSettingFactory(key="escrow.courier_link_hours", value="0")
    p = paid()
    token = services.courier_token(p, seller=p.seller)
    with pytest.raises(errors.InvalidCourierLink):
        services.payment_for_courier(token)


# --- Refunds and cancellations -------------------------------------------------------------------


def test_cancel_before_shipping_refunds_everything():
    p = paid()
    services.cancel(p, actor=p.buyer)
    p.refresh_from_db()
    assert p.status == S.REFUNDED and p.end_reason == "buyer_cancelled"
    assert p.refunded_minor == 11_330
    b = balances(p)
    assert b["cash"] == 0 and b["seller_pending"] == 0 and b["fees_pending"] == 0
    assert Notification.objects.filter(user=p.buyer, event_key="payments.refunded").exists()
    assert Notification.objects.filter(user=p.seller, event_key="payments.sale_cancelled").exists()

    other = paid()
    services.cancel(other, actor=other.seller)
    assert Payment.objects.get(pk=other.pk).end_reason == "seller_cancelled"


def test_no_cancellation_once_shipped_or_by_strangers():
    p = shipped()
    with pytest.raises(errors.InvalidTransition):
        services.cancel(p, actor=p.buyer)
    with pytest.raises(errors.PaymentNotFound):
        services.cancel(p, actor=adult("Zoé"))


def test_partial_refund_after_a_dispute_keeps_the_protection_fee():
    commission(500)
    p = shipped()
    services.open_dispute(p, by=p.buyer, reason="damaged")
    services.refund_partial(p, 4_000, actor=None, reason="dispute_partial")
    p.refresh_from_db()
    assert p.status == S.PARTIALLY_REFUNDED and p.refunded_minor == 4_000
    assert p.commission_minor == 300
    b = balances(p)
    assert b["seller_available"] == 6_700 and b["commissions"] == 300
    assert b["protection"] == 330 and b["seller_pending"] == 0
    assert b["refunds"] == 0 and b["cash"] == 11_330 - 4_000
    assert ledger.is_balanced()


@pytest.mark.parametrize("amount", [0, -5, 11_000, 20_000, 10.5])
def test_partial_refund_amounts_are_checked(amount):
    p = shipped()
    services.open_dispute(p, by=p.buyer, reason="damaged")
    with pytest.raises(errors.InvalidRefundAmount):
        services.refund_partial(p, amount, actor=None, reason="x")


def test_partial_refund_beyond_the_items_takes_from_the_delivery():
    commission(500)
    p = shipped()
    services.open_dispute(p, by=p.buyer, reason="damaged")
    services.refund_partial(p, 10_500, actor=None, reason="dispute_partial")
    p.refresh_from_db()
    assert p.commission_minor == 0
    assert balances(p)["seller_available"] == 500


# --- The state machine ---------------------------------------------------------------------------


def test_every_move_is_declared_and_checked():
    statuses = list(S.values)
    for current, target in itertools.product(statuses, statuses):
        assert common.can_move(current, target) == (target in ALLOWED[current])
    p = payment()
    for target in statuses:
        if target in ALLOWED[S.PENDING_PAYMENT]:
            continue
        with pytest.raises(errors.InvalidTransition):
            common.move(p, target)
    with pytest.raises(errors.PaymentNotFound):
        common.locked("00000000-0000-0000-0000-000000000000")


def test_finished_payments_cannot_move():
    p = paid()
    services.release(p, reason="test")
    for step in (
        lambda: services.release(p, reason="again"),
        lambda: services.refund_full(p, reason="again"),
        lambda: services.ship(p, actor=p.seller),
        lambda: services.open_dispute(p, by=p.buyer, reason="damaged"),
    ):
        with pytest.raises((errors.InvalidTransition, errors.DisputeNotAllowed)):
            step()


def test_owning_modules_hear_every_change():
    heard = []
    services.listen("test_order", lambda p: heard.append(p.status))
    try:
        p = paid(source_type="test_order")
        services.release(p, reason="test")
    finally:
        services.forget("test_order")
    assert heard == [S.HELD, S.RELEASED]


def test_every_move_is_in_the_audit_journal():
    from apps.core.audit.models import AuditEvent

    p = shipped()
    actions = list(AuditEvent.objects.filter(target_id=str(p.pk)).values_list("action", flat=True))
    assert {"payments.created", "payments.held", "payments.shipped"} <= set(actions)


def test_a_reference_already_taken_is_drawn_again(monkeypatch):
    from apps.payments.services import payments as payment_services

    taken = payment().reference
    draws = iter([taken, "SG-NEWONE22"])
    monkeypatch.setattr(payment_services, "_new_reference", lambda: next(draws))
    assert payment().reference == "SG-NEWONE22"


def test_balance_of_one_payment():
    first, second = paid(), paid()
    cash = ledger.account("provider_cash", "XOF", provider="fake")
    assert ledger.balance(cash, payment=first) == 11_330
    assert ledger.balance(cash) == 2 * 11_330 and second.total_minor == 11_330
