"""A cart of several shops paid in one go: one provider page and answer, then each payment
lives on its own (its seller, its code, its ledger entries)."""

import pytest

from apps.messaging.tests.factories import adult
from apps.payments import errors, services
from apps.payments.models import Payment, ReconciliationItem
from apps.payments.providers import EventKind
from apps.payments.providers.fake import FakeProvider, signed_event
from apps.payments.services import groups, webhooks
from apps.payments.services.reconciliation import reconcile

from .factories import balances, payment, seller

pytestmark = pytest.mark.django_db
S = Payment.Status


@pytest.fixture
def cart():
    client = adult("Awa")
    first = payment(client, seller("Gloria Make-up"))
    second = payment(client, seller("Inès Ongles"), items_minor=2_500, delivery_minor=0)
    return client, [first, second]


def webhook(kind, group, amount=None):
    body, headers = signed_event(
        kind, group.provider_reference, group.total_minor if amount is None else amount, "XOF"
    )
    return webhooks.handle("fake", headers, body)


def test_a_group_adds_up_its_payments(cart):
    client, payments = cart
    group = services.create_group(client, payments)
    assert group.total_minor == 11_330 + 2_600 and group.reference.startswith("SG-")
    assert str(group) == group.reference and group.description.endswith(group.reference)
    assert all(p.group == group for p in Payment.objects.all())
    assert services.group_status(group) == "pending"


def test_a_group_needs_payments_of_the_same_kind(cart):
    client, payments = cart
    with pytest.raises(errors.InvalidPayment):
        services.create_group(client, [])
    with pytest.raises(errors.InvalidPayment):
        services.create_group(adult("Inès"), payments)
    euro = payment(client, seller("Lina Paris"), currency="EUR")
    with pytest.raises(errors.InvalidPayment):
        services.create_group(client, [payments[0], euro])
    services.create_group(client, payments)
    with pytest.raises(errors.InvalidPayment):  # already grouped
        services.create_group(client, payments)


def test_paid_in_one_go_then_each_payment_on_its_own(cart):
    client, payments = cart
    group = services.start_group_checkout(services.create_group(client, payments), buyer=client)
    assert group.checkout_url.endswith(f"/pay/test/group/{group.pk}")
    assert services.start_group_checkout(group, buyer=client) == group  # the same page
    # A payment of the group is not paid alone.
    with pytest.raises(errors.InvalidTransition):
        services.start_checkout(payments[0], buyer=client)
    [event] = webhook(EventKind.PAYMENT_SUCCEEDED, group)
    assert event.status == "processed"
    group.refresh_from_db()
    assert group.paid_at and services.group_status(group) == "paid"
    first, second = (Payment.objects.get(pk=p.pk) for p in payments)
    assert first.status == second.status == S.HELD
    assert balances(first)["cash"] == group.total_minor
    # The same news twice changes nothing.
    assert groups.mark_group_paid(group, amount_minor=1, currency="XOF", key="again") == group
    with pytest.raises(errors.InvalidTransition):
        services.start_group_checkout(group, buyer=client)


def test_the_provider_fee_is_shared_in_proportion(cart):
    client, payments = cart
    group = services.create_group(client, payments)
    groups.mark_group_paid(
        group, amount_minor=group.total_minor, currency="xof", fee_minor=100, key="k"
    )
    assert balances(payments[0])["fees"] == 100


def test_a_wrong_amount_is_refused(cart):
    client, payments = cart
    group = services.start_group_checkout(services.create_group(client, payments), buyer=client)
    [event] = webhook(EventKind.PAYMENT_SUCCEEDED, group, amount=10)
    assert event.status == "failed"
    assert not Payment.objects.filter(status=S.HELD).exists()


def test_failed_or_given_up(cart):
    client, payments = cart
    group = services.start_group_checkout(services.create_group(client, payments), buyer=client)
    webhook(EventKind.PAYMENT_CANCELLED, group)
    assert services.group_status(group) == "cancelled"
    assert set(Payment.objects.values_list("status", flat=True)) == {S.CANCELLED}


def test_only_the_client_opens_the_payment_page(cart):
    client, payments = cart
    group = services.create_group(client, payments)
    with pytest.raises(errors.PaymentNotFound):
        services.start_group_checkout(group, buyer=adult("Inès"))


def test_reconciliation_counts_a_group_as_one_charge(cart):
    client, payments = cart
    group = services.start_group_checkout(services.create_group(client, payments), buyer=client)
    webhook(EventKind.PAYMENT_SUCCEEDED, group)
    statement = FakeProvider().transactions(
        group.created_at.replace(year=2000), group.created_at.replace(year=2100)
    )
    assert [(t.reference, t.amount_minor) for t in statement] == [
        (group.provider_reference, group.total_minor)
    ]
    run = reconcile("fake")
    assert run.discrepancies == 0 and not ReconciliationItem.objects.exists()


def test_a_reference_already_taken_is_drawn_again(cart, monkeypatch):
    client, payments = cart
    taken = services.create_group(client, [payments[0]]).reference
    drawn = iter([taken, "SG-NEWONE22"])
    monkeypatch.setattr(groups.payment_services, "_new_reference", lambda: next(drawn))
    assert services.create_group(client, [payments[1]]).reference == "SG-NEWONE22"


def test_only_the_two_parties_may_cancel(cart):
    from .factories import paid

    held = paid()
    assert not services.may_cancel(held, None)
    assert not services.may_cancel(held, adult("Stranger"))
    assert services.may_cancel(held, held.buyer)
    assert not services.may_cancel(payment(), adult("Awa"))  # not paid yet
    waiting = payment()
    assert not services.may_cancel(waiting, waiting.buyer)
