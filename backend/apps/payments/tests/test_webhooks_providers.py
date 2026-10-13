"""Webhooks: only the provider's, each event once; FedaPay and Stripe as their APIs say."""

import json
import time

import httpx
import pytest
import respx
from django.test import override_settings

from apps.payments import services
from apps.payments.models import JournalEntry, Payment, Payout, Refund, WebhookEvent
from apps.payments.providers import (
    EventKind,
    InvalidSignature,
    ProviderError,
    ProviderNotConfigured,
    get_provider,
    provider_for,
)
from apps.payments.providers.base import sign
from apps.payments.providers.fake import FakeProvider, signed_event
from apps.payments.services import webhooks

from .factories import balances, paid, payment

pytestmark = pytest.mark.django_db
S = Payment.Status


def checkout(p=None):
    p = p or payment()
    services.start_checkout(p, buyer=p.buyer)
    return p


def send(kind, reference, amount, currency="XOF"):
    body, headers = signed_event(kind, reference, amount, currency)
    return webhooks.handle("fake", headers, body), body, headers


# --- The test provider's webhooks ----------------------------------------------------------------


def test_payment_succeeded_is_processed_once():
    p = checkout()
    handled, body, headers = send(EventKind.PAYMENT_SUCCEEDED, p.provider_reference, 11_330)
    assert handled[0].status == WebhookEvent.Status.PROCESSED
    assert webhooks.handle("fake", headers, body) == []  # the same event again
    p.refresh_from_db()
    assert p.status == S.HELD and JournalEntry.objects.filter(payment=p).count() == 1
    assert str(handled[0]).startswith("fake payment.succeeded")


@pytest.mark.parametrize("kind", [EventKind.PAYMENT_FAILED, EventKind.PAYMENT_CANCELLED])
def test_failed_or_abandoned(kind):
    p = checkout()
    send(kind, p.provider_reference, None)
    p.refresh_from_db()
    assert p.status == S.CANCELLED


def test_a_wrong_amount_is_kept_for_the_finance_team():
    p = checkout()
    handled, _, _ = send(EventKind.PAYMENT_SUCCEEDED, p.provider_reference, 1)
    assert handled[0].status == WebhookEvent.Status.FAILED
    assert handled[0].error.startswith("invalid_payment")
    p.refresh_from_db()
    assert p.status == S.PENDING_PAYMENT


@pytest.mark.parametrize(
    "kind",
    [
        EventKind.PAYMENT_SUCCEEDED,
        EventKind.REFUND_SUCCEEDED,
        EventKind.PAYOUT_PAID,
        "something.else",
    ],
)
def test_unknown_references_and_kinds_are_ignored(kind):
    handled, _, _ = send(kind, "nobody", 100)
    assert handled[0].status == WebhookEvent.Status.IGNORED


def test_refund_and_payout_events():
    p = paid()
    services.cancel(p, actor=p.buyer)
    refund = Refund.objects.get(payment=p)
    assert refund.status == Refund.Status.SUCCEEDED  # through a fake webhook
    other = paid()
    Payment.objects.filter(pk=other.pk).update(provider="fake")
    services.cancel(other, actor=other.buyer)
    refund = Refund.objects.get(payment=other)
    Refund.objects.filter(pk=refund.pk).update(status=Refund.Status.PENDING)
    send(EventKind.REFUND_FAILED, refund.provider_reference, refund.amount_minor)
    # Already succeeded in the ledger: a late failure news changes nothing there.
    assert balances(other)["refunds"] == 0


def test_payout_events_from_the_provider():
    p = paid()
    services.confirm_receipt(p, services.receipt_code_for(p, p.buyer), actor=p.seller)
    services.save_payout_method(p.seller, currency="XOF", kind="fake", details={})
    payout = services.request_payout(p.seller, amount_minor=11_000, currency="XOF")
    payout.refresh_from_db()
    assert payout.status == Payout.Status.PAID
    failed = Payout.objects.create(
        seller=p.seller,
        amount_minor=10,
        currency="XOF",
        provider="fake",
        destination="x",
        provider_reference="fake_payout_x",
        status=Payout.Status.PROCESSING,
    )
    send(EventKind.PAYOUT_FAILED, "fake_payout_x", 10)
    failed.refresh_from_db()
    assert failed.status == Payout.Status.FAILED


def test_forged_or_old_webhooks_are_refused():
    body = json.dumps({"id": "e", "type": "payment.succeeded", "reference": "r"}).encode()
    with pytest.raises(InvalidSignature):
        webhooks.handle("fake", {"X-Fake-Signature": "t=1,v1=00"}, body)
    with pytest.raises(InvalidSignature):
        webhooks.handle("fake", {}, body)
    with pytest.raises(InvalidSignature):
        webhooks.handle("fake", {"X-Fake-Signature": "t=abc,v1=00"}, body)
    now = int(time.time())
    forged = sign("not-the-secret", now, body)
    with pytest.raises(InvalidSignature):
        webhooks.handle("fake", {"X-Fake-Signature": f"t={now},v1={forged}"}, body)
    with pytest.raises(ProviderNotConfigured):
        webhooks.handle("nobody", {}, body)


def test_an_unexpected_error_records_nothing_so_the_provider_retries(monkeypatch):
    p = checkout()

    def broken(provider, event):
        raise RuntimeError("database down")

    monkeypatch.setattr(webhooks, "_dispatch", broken)
    with pytest.raises(RuntimeError):
        send(EventKind.PAYMENT_SUCCEEDED, p.provider_reference, 11_330)
    assert not WebhookEvent.objects.exists()


def test_same_event_arriving_twice_at_the_same_moment(monkeypatch):
    p = checkout()
    body, headers = signed_event(EventKind.PAYMENT_SUCCEEDED, p.provider_reference, 11_330, "XOF")
    event_id = json.loads(body)["id"]
    real_exists = WebhookEvent.objects.filter

    def late_check(*args, **kwargs):
        # The other process stored it just after our check.
        WebhookEvent.objects.get_or_create(
            provider="fake", event_id=event_id, defaults={"kind": "x", "status": "processed"}
        )
        return WebhookEvent.objects.none()

    monkeypatch.setattr(WebhookEvent.objects, "filter", late_check)
    assert webhooks.handle("fake", headers, body) == []
    monkeypatch.setattr(WebhookEvent.objects, "filter", real_exists)


# --- Provider choice -----------------------------------------------------------------------------


def test_provider_choice_per_country():
    assert provider_for("BJ").name == "fake"  # FedaPay without keys, test provider allowed
    with override_settings(PAYMENTS_FAKE_ENABLED=False):
        with pytest.raises(ProviderNotConfigured):
            provider_for("FR")
        with pytest.raises(ProviderNotConfigured):
            FakeProvider()
    with pytest.raises(ProviderNotConfigured):
        get_provider("paypal")


def test_the_test_provider_statement_is_our_own():
    from django.utils import timezone

    p = paid(checkout())
    start = timezone.now().replace(year=2000)
    rows = FakeProvider().transactions(start, timezone.now())
    assert [(r.reference, r.amount_minor) for r in rows] == [(p.provider_reference, 11_330)]


# --- FedaPay -------------------------------------------------------------------------------------

FEDAPAY = {
    "FEDAPAY_SECRET_KEY": "sk_sandbox_x",
    "FEDAPAY_WEBHOOK_SECRET": "wh_sandbox_x",
    "FEDAPAY_ENVIRONMENT": "sandbox",
}


@override_settings(**FEDAPAY)
@respx.mock
def test_fedapay_checkout_payout_and_webhook():
    base = "https://sandbox-api.fedapay.com/v1"
    created = respx.post(f"{base}/transactions").mock(
        return_value=httpx.Response(200, json={"v1/transaction": {"id": 77, "status": "pending"}})
    )
    respx.post(f"{base}/transactions/77/token").mock(
        return_value=httpx.Response(200, json={"token": "t", "url": "https://pay.fedapay/x"})
    )
    p = payment()
    provider = get_provider("fedapay")
    result = provider.create_checkout(p, return_url="https://solange/back")
    assert (result.reference, result.url) == ("77", "https://pay.fedapay/x")
    sent = json.loads(created.calls[0].request.content)
    assert sent["amount"] == 11_330 and sent["currency"] == {"iso": "XOF"}
    assert created.calls[0].request.headers["Authorization"] == "Bearer sk_sandbox_x"

    respx.post(f"{base}/payouts").mock(
        return_value=httpx.Response(200, json={"v1/payout": {"id": 9}})
    )
    start = respx.put(f"{base}/payouts/start").mock(return_value=httpx.Response(200, json=[]))
    payout = Payout(amount_minor=6_000, currency="XOF")
    answer = provider.payout(payout, {"number": "97123456", "firstname": "Aïcha"})
    assert answer.reference == "9" and answer.status == "pending"
    assert json.loads(start.calls[0].request.content)[0]["id"] == 9
    assert provider.refund(p, None).status == "manual"  # no refund API at FedaPay

    body = json.dumps(
        {
            "id": "evt_1",
            "name": "transaction.approved",
            "entity": {"id": 77, "amount": 11_330, "currency": {"iso": "XOF"}, "fees": 170},
        }
    ).encode()
    now = int(time.time())
    header = f"t={now},s={sign('wh_sandbox_x', now, body)}"
    [event] = provider.parse_webhook({"X-FEDAPAY-SIGNATURE": header}, body)
    assert (event.kind, event.reference, event.fee_minor) == (
        EventKind.PAYMENT_SUCCEEDED,
        "77",
        170,
    )

    respx.get(f"{base}/transactions?per_page=500").mock(
        return_value=httpx.Response(
            200,
            json={"v1/transactions": [{"id": 77, "amount": 11_330, "status": "approved"}]},
        )
    )
    assert provider.transactions(None, None)[0].reference == "77"


@override_settings(**FEDAPAY)
@respx.mock
def test_fedapay_errors():
    respx.post("https://sandbox-api.fedapay.com/v1/transactions").mock(
        return_value=httpx.Response(401, json={"message": "Unauthorized"})
    )
    with pytest.raises(ProviderError):
        get_provider("fedapay").create_checkout(payment(), return_url="x")
    respx.post("https://sandbox-api.fedapay.com/v1/payouts").mock(
        side_effect=httpx.ConnectError("down")
    )
    with pytest.raises(ProviderError):
        get_provider("fedapay").payout(Payout(amount_minor=1, currency="XOF"), {"number": "1"})


def test_fedapay_and_stripe_are_off_without_keys():
    with pytest.raises(ProviderNotConfigured):
        get_provider("fedapay")
    with pytest.raises(ProviderNotConfigured):
        get_provider("stripe")


# --- Stripe --------------------------------------------------------------------------------------

STRIPE = {"STRIPE_SECRET_KEY": "sk_test_x", "STRIPE_WEBHOOK_SECRET": "whsec_x"}


@override_settings(**STRIPE)
@respx.mock
def test_stripe_checkout_refund_transfer_and_webhooks():
    api = "https://api.stripe.com/v1"
    session = respx.post(f"{api}/checkout/sessions").mock(
        return_value=httpx.Response(200, json={"id": "cs_1", "url": "https://checkout.stripe/x"})
    )
    p = payment(currency="EUR", items_minor=2_000, delivery_minor=0)
    provider = get_provider("stripe")
    result = provider.create_checkout(p, return_url="https://solange/back")
    assert result.reference == "cs_1"
    form = session.calls[0].request.content.decode()
    assert "transfer_group" in form and str(p.total_minor) in form

    p.provider_reference = "cs_1"
    respx.get(f"{api}/checkout/sessions/cs_1").mock(
        return_value=httpx.Response(200, json={"payment_intent": "pi_1"})
    )
    respx.post(f"{api}/refunds").mock(
        return_value=httpx.Response(200, json={"id": "re_1", "status": "succeeded"})
    )
    refund = Refund(amount_minor=500, currency="EUR")
    assert provider.refund(p, refund).status == "succeeded"
    respx.post(f"{api}/transfers").mock(return_value=httpx.Response(200, json={"id": "tr_1"}))
    transfer = provider.payout(Payout(amount_minor=1_000, currency="EUR"), {"account": "acct_1"})
    assert (transfer.reference, transfer.status) == ("tr_1", "paid")

    def stripe_event(kind, obj):
        body = json.dumps({"id": f"evt_{kind}", "type": kind, "data": {"object": obj}}).encode()
        now = int(time.time())
        header = f"t={now},v1={sign('whsec_x', now, body)}"
        return provider.parse_webhook({"Stripe-Signature": header}, body)[0]

    paid_event = stripe_event(
        "checkout.session.completed",
        {"id": "cs_1", "payment_status": "paid", "amount_total": 2_060, "currency": "eur"},
    )
    assert (paid_event.kind, paid_event.currency) == (EventKind.PAYMENT_SUCCEEDED, "EUR")
    assert stripe_event("checkout.session.async_payment_succeeded", {"id": "cs"}).kind == (
        EventKind.PAYMENT_SUCCEEDED
    )
    assert stripe_event("checkout.session.async_payment_failed", {}).kind == (
        EventKind.PAYMENT_FAILED
    )
    assert stripe_event("checkout.session.expired", {}).kind == EventKind.PAYMENT_CANCELLED
    assert stripe_event("refund.updated", {"status": "failed"}).kind == EventKind.REFUND_FAILED
    assert stripe_event("refund.created", {"status": "succeeded"}).kind == (
        EventKind.REFUND_SUCCEEDED
    )
    assert stripe_event("customer.created", {}).kind == EventKind.OTHER

    respx.get(url__startswith=f"{api}/balance_transactions").mock(
        return_value=httpx.Response(
            200, json={"data": [{"source": "ch_1", "amount": 2_060, "currency": "eur", "fee": 60}]}
        )
    )
    from django.utils import timezone

    rows = provider.transactions(timezone.now(), timezone.now())
    assert rows[0].fee_minor == 60 and rows[0].currency == "EUR"


@override_settings(**STRIPE)
@respx.mock
def test_stripe_errors():
    respx.post("https://api.stripe.com/v1/checkout/sessions").mock(
        return_value=httpx.Response(402, json={"error": {}})
    )
    with pytest.raises(ProviderError):
        get_provider("stripe").create_checkout(payment(), return_url="x")
    respx.post("https://api.stripe.com/v1/transfers").mock(side_effect=httpx.ConnectError("x"))
    with pytest.raises(ProviderError):
        get_provider("stripe").payout(Payout(amount_minor=1, currency="EUR"), {"account": "a"})
