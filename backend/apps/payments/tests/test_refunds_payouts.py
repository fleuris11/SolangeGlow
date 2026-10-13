"""Refunds and payouts through the providers, and the ledger at each answer."""

import json

import pytest
from django.test import override_settings

from apps.core import crypto
from apps.core.tests.factories import PlatformSettingFactory
from apps.messaging.tests.factories import adult
from apps.notifications.models import Notification
from apps.payments import errors, services
from apps.payments.models import Payout, PayoutMethod, Refund
from apps.payments.providers import (
    PROVIDERS,
    PayoutResult,
    ProviderError,
    ProviderNotConfigured,
    RefundResult,
)
from apps.payments.services import payouts as payout_services
from apps.payments.services import refunds as refund_services
from apps.pros.models import ProProfile

from .factories import balances, code_of, paid, seller

pytestmark = pytest.mark.django_db


class StubProvider:
    """A provider whose answers the test chooses."""

    name = "stub"
    refund_answer = RefundResult("stub_refund", "pending")
    payout_answer = PayoutResult("stub_payout", "pending")
    error: Exception | None = None
    details: dict = {}

    def refund(self, payment, refund):
        if self.error:
            raise self.error
        return self.refund_answer

    def payout(self, payout, details):
        if self.error:
            raise self.error
        StubProvider.details = details
        return self.payout_answer


@pytest.fixture
def stub(monkeypatch):
    monkeypatch.setitem(PROVIDERS, "stub", StubProvider)
    StubProvider.error = None
    StubProvider.refund_answer = RefundResult("stub_refund", "pending")
    StubProvider.payout_answer = PayoutResult("stub_payout", "pending")
    return StubProvider


def refunded_with(stub_provider):
    p = paid()
    type(p).objects.filter(pk=p.pk).update(provider="stub")
    p.refresh_from_db()
    services.cancel(p, actor=p.buyer)
    return Refund.objects.get(payment=p)


# --- Refunds -------------------------------------------------------------------------------------


def test_the_test_provider_confirms_refunds():
    p = paid()
    services.cancel(p, actor=p.buyer)
    refund = Refund.objects.get(payment=p)
    assert refund.status == Refund.Status.SUCCEEDED and refund.completed_at
    assert balances(p)["cash"] == 0 and balances(p)["refunds"] == 0
    assert str(refund).endswith("-11330 XOF")


def test_refund_waiting_for_the_provider_then_confirmed(stub):
    refund = refunded_with(stub)
    assert refund.status == Refund.Status.PENDING and refund.provider_reference == "stub_refund"
    assert balances(refund.payment)["refunds"] == 11_330
    refund_services.refund_succeeded(refund)
    refund_services.refund_succeeded(refund)  # twice: counted once
    assert balances(refund.payment)["refunds"] == 0


def test_refund_done_at_once_by_the_provider(stub):
    stub.refund_answer = RefundResult("stub_refund", "succeeded")
    assert refunded_with(stub).status == Refund.Status.SUCCEEDED


def test_refund_to_do_by_hand(stub):
    stub.refund_answer = RefundResult("", "manual")
    refund = refunded_with(stub)
    assert refund.status == Refund.Status.MANUAL
    refund_services.mark_done_by_hand(refund, actor=adult("Solange"))
    refund.refresh_from_db()
    assert refund.status == Refund.Status.SUCCEEDED and balances(refund.payment)["refunds"] == 0


def test_refund_without_provider_keys_is_done_by_hand(stub):
    stub.error = ProviderNotConfigured("off")
    assert refunded_with(stub).status == Refund.Status.MANUAL


def test_refund_network_failure_stays_pending_then_fails(stub):
    stub.error = ProviderError("timeout")
    refund = refunded_with(stub)
    assert refund.status == Refund.Status.PENDING and refund.error == "timeout"
    refund_services.refund_failed(refund, error="declined")
    refund.refresh_from_db()
    assert refund.status == Refund.Status.FAILED
    assert refund_services.refund_failed(refund, error="again").error == "declined"
    # Money still owed to the client until done by hand.
    assert balances(refund.payment)["refunds"] == 11_330
    assert refund_services.start_refund(refund.pk).status == Refund.Status.FAILED


# --- Payouts -------------------------------------------------------------------------------------


def released_seller():
    p = paid()
    services.confirm_receipt(p, code_of(p), actor=p.seller)
    return p.seller, p


def test_payout_method_is_encrypted_and_masked():
    aicha = seller()
    method = services.save_payout_method(
        aicha,
        currency="xof",
        kind=PayoutMethod.Kind.MOBILE_MONEY,
        details={"operator": "MTN", "number": "97123456", "firstname": "Aïcha"},
    )
    assert method.display == "MTN •••• 3456" and "97123456" not in method.details_secret
    assert json.loads(crypto.decrypt(method.details_secret))["number"] == "97123456"
    stripe = services.save_payout_method(
        aicha, currency="EUR", kind=PayoutMethod.Kind.STRIPE, details={"account": "acct_123456"}
    )
    assert stripe.display == "Stripe •••• 3456" and str(stripe).endswith("Stripe •••• 3456")
    fake = services.save_payout_method(
        aicha, currency="XOF", kind=PayoutMethod.Kind.FAKE, details={"label": "Test"}
    )
    assert fake.display == "Test" and PayoutMethod.objects.filter(seller=aicha).count() == 2


def test_a_payout_with_the_test_provider():
    aicha, p = released_seller()
    services.save_payout_method(aicha, currency="XOF", kind="fake", details={"label": "Test"})
    payout = services.request_payout(aicha, amount_minor=11_000, currency="XOF")
    payout.refresh_from_db()
    assert payout.status == Payout.Status.PAID and payout.paid_at
    b = balances(p)
    assert b["seller_available"] == 0 and b["payouts"] == 0 and b["cash"] == 330
    assert Notification.objects.filter(user=aicha, event_key="payouts.paid").exists()
    assert str(payout).endswith("11000 XOF")


def test_payout_rules():
    aicha, _ = released_seller()
    with pytest.raises(errors.NoPayoutMethod):
        services.request_payout(aicha, amount_minor=6_000, currency="XOF")
    services.save_payout_method(aicha, currency="XOF", kind="fake", details={})
    with pytest.raises(errors.BelowMinimum):
        services.request_payout(aicha, amount_minor=4_999, currency="XOF")
    with pytest.raises(errors.BelowMinimum):
        services.request_payout(aicha, amount_minor=5_000.5, currency="XOF")
    with pytest.raises(errors.NotEnoughMoney):
        services.request_payout(aicha, amount_minor=11_001, currency="XOF")


def test_payout_needs_a_checked_identity():
    aicha, _ = released_seller()
    ProProfile.objects.filter(user=aicha).update(verification_status=ProProfile.Verification.NONE)
    aicha.refresh_from_db()
    services.save_payout_method(aicha, currency="XOF", kind="fake", details={})
    with pytest.raises(errors.IdentityNeeded):
        services.request_payout(aicha, amount_minor=6_000, currency="XOF")


def test_a_seller_without_showcase_can_ask_for_her_money():
    client = adult("Inès")
    PlatformSettingFactory(key="payments.payout_minimum", value='{"XOF": 0}', value_type="json")
    services.save_payout_method(client, currency="XOF", kind="fake", details={})
    with pytest.raises(errors.NotEnoughMoney):
        services.request_payout(client, amount_minor=1, currency="XOF")


@pytest.fixture
def mobile_money(stub):
    """Payouts of the seller go through the stub provider (Mobile Money method)."""
    PlatformSettingFactory(key="payments.providers", value='{"BJ": "stub"}', value_type="json")
    aicha, p = released_seller()
    services.save_payout_method(
        aicha,
        currency="XOF",
        kind="mobile_money",
        details={"operator": "MTN", "number": "97123456"},
    )
    return aicha, p


def test_payout_waiting_for_the_provider_then_paid(mobile_money, stub):
    aicha, p = mobile_money
    payout = services.request_payout(aicha, amount_minor=11_000, currency="XOF")
    payout.refresh_from_db()
    assert payout.status == Payout.Status.PROCESSING and payout.provider == "stub"
    assert stub.details["number"] == "97123456"
    assert balances(p)["payouts"] == 11_000
    payout_services.payout_paid(payout)
    assert payout_services.payout_paid(payout).status == Payout.Status.PAID
    assert balances(p)["payouts"] == 0
    assert payout_services.execute_payout(payout.pk).status == Payout.Status.PAID


def test_payout_paid_at_once(mobile_money, stub):
    stub.payout_answer = PayoutResult("stub_payout", "paid")
    aicha, _ = mobile_money
    payout = services.request_payout(aicha, amount_minor=11_000, currency="XOF")
    payout.refresh_from_db()
    assert payout.status == Payout.Status.PAID


def test_payout_network_failure_then_refused(mobile_money, stub):
    stub.error = ProviderError("timeout")
    aicha, p = mobile_money
    payout = services.request_payout(aicha, amount_minor=11_000, currency="XOF")
    payout.refresh_from_db()
    assert payout.status == Payout.Status.REQUESTED and payout.error == "timeout"
    payout_services.payout_failed(payout, error="number unknown")
    payout.refresh_from_db()
    assert payout.status == Payout.Status.FAILED
    assert payout_services.payout_failed(payout, error="again").error == "number unknown"
    # The money is available again.
    assert balances(p)["seller_available"] == 11_000 and balances(p)["payouts"] == 0
    assert Notification.objects.filter(user=aicha, event_key="payouts.failed").exists()


def test_payout_without_provider_keys_gives_the_money_back(mobile_money, stub):
    stub.error = ProviderNotConfigured("off")
    aicha, p = mobile_money
    payout = services.request_payout(aicha, amount_minor=11_000, currency="XOF")
    payout.refresh_from_db()
    assert payout.status == Payout.Status.FAILED and balances(p)["seller_available"] == 11_000


def test_payout_method_removed_meanwhile(mobile_money, stub):
    aicha, _ = mobile_money
    stub.error = ProviderError("timeout")
    payout = services.request_payout(aicha, amount_minor=11_000, currency="XOF")
    PayoutMethod.objects.filter(seller=aicha).delete()
    assert payout_services.execute_payout(payout.pk).status == Payout.Status.FAILED


@override_settings(PAYMENTS_FAKE_ENABLED=False)
def test_no_payout_where_no_provider_is_configured():
    aicha = seller()
    services.save_payout_method(aicha, currency="XOF", kind="mobile_money", details={})
    with pytest.raises(errors.PaymentsUnavailable):
        services.request_payout(aicha, amount_minor=6_000, currency="XOF")
