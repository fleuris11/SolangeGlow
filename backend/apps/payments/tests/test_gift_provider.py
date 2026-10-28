"""Payments paid with the money of a gift (ADR-014): no provider page, held at once, a
refund goes back onto the gift through the internal provider « gift »."""

import pytest

from apps.messaging.tests.factories import adult
from apps.payments import errors, ledger, services
from apps.payments.models import LedgerAccount, Payment, Refund
from apps.payments.providers import ProviderError, ProviderNotConfigured, get_provider
from apps.payments.providers import gift as gift_provider
from apps.payments.services import refunds, webhooks

from .factories import paid, payment, seller

pytestmark = pytest.mark.django_db
S = Payment.Status


@pytest.fixture
def credited(monkeypatch):
    calls = []
    monkeypatch.setattr(gift_provider, "_refund_callbacks", [lambda p, r: calls.append(r)])
    return calls


def test_a_payment_without_buyer_protection():
    plain = payment(with_buyer_fee=False)
    assert plain.buyer_fee_minor == 0 and plain.buyer_fee_rule is None
    assert plain.total_minor == 11_000


def test_paid_by_a_gift_then_refunded_onto_it(credited):
    held = services.pay_from_gift(payment(with_buyer_fee=False), key="gift:1:2", tell_buyer=False)
    assert held.status == S.HELD and held.provider == "gift"
    assert held.provider_reference == "gift:1:2" and held.checkout_url == ""
    assert services.receipt_code_of(held) is not None
    cash = ledger.account(LedgerAccount.Kind.PROVIDER_CASH, "XOF", provider="gift")
    assert ledger.balance(cash) == 11_000
    services.refund_full(held, reason="test")
    refund = Refund.objects.get(payment=held)
    assert refund.status == Refund.Status.SUCCEEDED and credited == [refund]
    assert ledger.balance(cash) == 0
    with pytest.raises(errors.InvalidTransition):
        services.pay_from_gift(held, key="again")


def test_only_a_pending_payment_in_fcfa(credited):
    euros = payment(currency="EUR", items_minor=2_000, delivery_minor=0)
    with pytest.raises(errors.InvalidTransition):
        services.pay_from_gift(euros, key="k")
    assert services.receipt_code_of(paid()) is not None
    assert services.receipt_code_of(payment()) is None


def test_a_whole_cart_paid_by_a_gift():
    client = adult("Awa")
    first = payment(client, seller("Gloria Make-up"))
    second = payment(client, seller("Inès Ongles"), items_minor=2_500, delivery_minor=0)
    group = services.create_group(client, [first, second])
    done = services.pay_group_from_gift(group, key="gift:card:1")
    assert done.paid_at and done.provider == "gift"
    assert set(Payment.objects.values_list("status", "provider")) == {(S.HELD, "gift")}
    with pytest.raises(errors.InvalidTransition):
        services.pay_group_from_gift(group, key="again")


def test_the_gift_provider_never_opens_a_page_nor_pays_out(monkeypatch):
    provider = get_provider("gift")
    with pytest.raises(ProviderError):
        provider.create_checkout(None, return_url="")
    with pytest.raises(ProviderError):
        provider.payout(None, {})
    assert provider.parse_webhook({}, b"") == [] and provider.transactions(None, None) == []
    with pytest.raises(ProviderNotConfigured):
        webhooks.handle("gift", {}, b"{}")
    monkeypatch.setattr(gift_provider, "_refund_callbacks", [])
    with pytest.raises(ProviderError):
        provider.refund(None, None)


def test_a_refund_without_its_module_stays_pending(monkeypatch):
    monkeypatch.setattr(gift_provider, "_refund_callbacks", [])
    held = services.pay_from_gift(payment(), key="gift:x")
    services.refund_full(held, reason="test")
    refund = Refund.objects.get(payment=held)
    assert refund.status == Refund.Status.PENDING and refund.error
    assert refunds.start_refund(refund.pk).status == Refund.Status.PENDING


def test_on_refund_registers_a_callback_once(monkeypatch):
    monkeypatch.setattr(gift_provider, "_refund_callbacks", [])

    def callback(payment, refund):
        return None

    gift_provider.on_refund(callback)
    gift_provider.on_refund(callback)
    assert gift_provider._refund_callbacks == [callback]
