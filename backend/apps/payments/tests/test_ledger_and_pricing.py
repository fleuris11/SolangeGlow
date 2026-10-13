"""The ledger refuses anything unbalanced and never changes; the most precise rule wins."""

import datetime

import pytest
from django.db import DatabaseError, transaction
from django.utils import timezone

from apps.payments import ledger, pricing
from apps.payments.ledger import LedgerError, Line, credit, debit
from apps.payments.models import JournalEntry, JournalLine, LedgerAccount, PricingRule

from .factories import seller

pytestmark = pytest.mark.django_db
Kind = LedgerAccount.Kind


@pytest.fixture
def accounts():
    return (
        ledger.account(Kind.PROVIDER_CASH, "XOF", provider="fake"),
        ledger.account(Kind.FEE_REVENUE, "XOF"),
        ledger.account(Kind.FEE_REVENUE, "EUR"),
    )


def test_a_balanced_entry_is_written_once(accounts):
    cash, revenue, _ = accounts
    entry = ledger.post("test", "key-1", [debit(cash, 500), credit(revenue, 500)])
    again = ledger.post("test", "key-1", [debit(cash, 999), credit(revenue, 999)])
    assert again.pk == entry.pk and entry.lines.count() == 2
    assert ledger.balance(cash) == 500 and ledger.balance(revenue) == 500
    assert ledger.is_balanced()


@pytest.mark.parametrize(
    "lines",
    [
        [],
        [Line(None, 0, 0)],
        "unbalanced",
        "mixed",
        "negative",
        "both",
        "float",
    ],
)
def test_entries_that_would_break_the_ledger_are_refused(accounts, lines):
    cash, revenue, euro = accounts
    cases = {
        "unbalanced": [debit(cash, 500), credit(revenue, 400)],
        "mixed": [debit(cash, 500), credit(euro, 500)],
        "negative": [debit(cash, -5), credit(revenue, -5)],
        "both": [Line(cash, 5, 5), credit(revenue, 0)],
        "float": [debit(cash, 5.0), credit(revenue, 5.0)],
    }
    lines = cases.get(lines, lines) if isinstance(lines, str) else lines
    with pytest.raises((LedgerError, AttributeError)):
        ledger.post("test", "bad", lines)
    assert not JournalEntry.objects.exists()


def test_zero_lines_are_left_out(accounts):
    cash, revenue, _ = accounts
    entry = ledger.post("test", "k", [debit(cash, 5), credit(revenue, 5), credit(revenue, 0)])
    assert entry.lines.count() == 2


def test_the_database_forbids_changing_the_ledger(accounts):
    cash, revenue, _ = accounts
    entry = ledger.post("test", "k", [debit(cash, 5), credit(revenue, 5)])
    with pytest.raises(DatabaseError), transaction.atomic():
        JournalLine.objects.filter(entry=entry).update(debit_minor=50)
    with pytest.raises(DatabaseError), transaction.atomic():
        JournalEntry.objects.filter(pk=entry.pk).delete()
    assert ledger.balance(cash) == 5


def test_a_key_written_meanwhile_returns_the_entry(accounts, monkeypatch):
    cash, revenue, _ = accounts
    first = ledger.post("test", "race", [debit(cash, 5), credit(revenue, 5)])
    # Simulate the other process: the existence check sees nothing, the insert collides.
    real_filter = JournalEntry.objects.filter
    calls = {"n": 0}

    def blind_filter(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return JournalEntry.objects.none()
        return real_filter(*args, **kwargs)

    monkeypatch.setattr(JournalEntry.objects, "filter", blind_filter)
    assert ledger.post("test", "race", [debit(cash, 5), credit(revenue, 5)]).pk == first.pk


def test_balances_per_owner_provider_and_payment(accounts):
    cash, revenue, _ = accounts
    other_cash = ledger.account(Kind.PROVIDER_CASH, "XOF", provider="stripe")
    ledger.post("t", "a", [debit(cash, 100), credit(revenue, 100)])
    ledger.post("t", "b", [debit(other_cash, 50), credit(revenue, 50)])
    assert ledger.balance_of(Kind.PROVIDER_CASH, "xof") == 150
    assert ledger.balance_of(Kind.PROVIDER_CASH, "XOF", provider="stripe") == 50
    assert ledger.balance_of(Kind.FEE_REVENUE, "XOF") == 150
    owner = seller()
    assert ledger.balance_of(Kind.SELLER_AVAILABLE, "XOF", owner=owner) == 0
    assert ledger.balance(cash, payment=None) == 100
    assert "XOF" in str(cash) and "fake" in str(cash)


# --- Pricing rules -------------------------------------------------------------------------------


def rule(**kwargs):
    values = {"kind": PricingRule.Kind.COMMISSION, "name": "r", "percent_bps": 100}
    values.update(kwargs)
    return PricingRule.objects.create(**values)


def test_the_most_precise_rule_wins():
    aicha = seller()
    general = rule(name="general", percent_bps=0)
    country = rule(name="BJ", country="BJ", percent_bps=300)
    category = rule(name="wigs", category="wigs", percent_bps=400)
    hers = rule(name="Aïcha", seller=aicha, percent_bps=200)
    criteria = {"currency": "XOF", "country": "BJ", "purpose": "order"}
    assert pricing.find_rule("commission", **criteria) == country
    assert pricing.find_rule("commission", category="wigs", **criteria) == category
    assert pricing.find_rule("commission", category="wigs", seller=aicha, **criteria) == hers
    assert pricing.find_rule("commission", currency="XOF", country="FR") == general


def test_dates_activity_currency_and_priority():
    now = timezone.now()
    rule(name="old", percent_bps=900, valid_until=now - datetime.timedelta(days=1))
    rule(name="future", percent_bps=900, valid_from=now + datetime.timedelta(days=1))
    rule(name="off", percent_bps=900, is_active=False)
    rule(name="euro", percent_bps=900, currency="EUR")
    low = rule(name="low", percent_bps=100, priority=0)
    high = rule(name="high", percent_bps=200, priority=5)
    assert pricing.find_rule("commission", currency="XOF") == high
    assert pricing.find_rule("commission", currency="XOF", at=now) != low
    assert str(high) == "high"


def test_amounts_rounding_fixed_min_and_max():
    r = rule(percent_bps=333, fixed_minor=10, min_minor=100, max_minor=1_000)
    assert pricing.amount_for(r, 10_000) == 343  # 333.0 + 10
    assert pricing.amount_for(r, 1_000) == 100  # 33 + 10 < min
    assert pricing.amount_for(r, 1_000_000) == 1_000  # max
    assert pricing.amount_for(rule(percent_bps=50), 1_001) == 5  # 5.005 rounds half up
    assert pricing.amount_for(rule(percent_bps=50), 999) == 5  # 4.995 rounds half up
    assert pricing.amount_for(None, 10_000) == 0
    assert pricing.amount_for(r, 0) == 0
    assert pricing.amount_for(rule(percent_bps=0, fixed_minor=-50), 100) == 0
    charge = pricing.charge("buyer_protection", 11_000, currency="XOF")
    assert charge.amount_minor == 330  # default rule of the migration: 3 %, min 100
    assert pricing.charge("buyer_protection", 1_000, currency="XOF").amount_minor == 100
    assert pricing.charge("buyer_protection", 1_000, currency="EUR").amount_minor == 30
