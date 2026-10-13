"""Statements of the providers against the ledger; DAC7 figures of the sellers."""

import datetime

import pytest
from django.utils import timezone

from apps.payments import services
from apps.payments.models import Payment, ReconciliationItem, SellerTaxProfile
from apps.payments.providers import PROVIDERS, Transaction
from apps.payments.services import reconciliation, tax
from apps.payments.tasks import reconcile_providers

from .factories import code_of, paid, payment, seller, shipped

pytestmark = pytest.mark.django_db
I = ReconciliationItem.Kind  # noqa: E741


class Statement:
    name = "statement"
    rows: list = []

    def transactions(self, since, until):
        return self.rows


@pytest.fixture
def statement(monkeypatch):
    monkeypatch.setitem(PROVIDERS, "statement", Statement)
    return Statement


def counted(reference, amount=11_330):
    p = paid()
    Payment.objects.filter(pk=p.pk).update(provider="statement", provider_reference=reference)
    return p


def test_differences_between_the_provider_and_the_ledger(statement):
    counted("same")
    counted("other_amount")
    counted("only_ours")
    statement.rows = [
        Transaction("same", 11_330, "XOF"),
        Transaction("other_amount", 11_000, "XOF"),
        Transaction("only_theirs", 5_000, "XOF"),
    ]
    run = reconciliation.reconcile("statement")
    found = {(i.kind, i.reference) for i in run.items.all()}
    assert found == {
        (I.AMOUNT_MISMATCH, "other_amount"),
        (I.MISSING_IN_LEDGER, "only_theirs"),
        (I.MISSING_AT_PROVIDER, "only_ours"),
    }
    assert run.checked == 3 and run.discrepancies == 3
    assert str(run).startswith("statement") and str(run.items.first())


def test_a_clean_day(statement):
    counted("same")
    statement.rows = [Transaction("same", 11_330, "XOF")]
    assert reconciliation.reconcile("statement").discrepancies == 0


def test_the_daily_task_skips_providers_without_keys():
    paid()
    runs = reconcile_providers()
    assert len(runs) == 1  # only the test provider is configured in the tests


def test_tax_profile_keeps_the_tax_number_encrypted():
    aicha = seller()
    profile = services.save_tax_profile(
        aicha,
        legal_name="Aïcha Hounkpè",
        is_business=True,
        address="Rue 12",
        city="Cotonou",
        country="BJ",
        tax_id="3201901234567",
    )
    assert profile.tax_id_hint == "•••• 4567" and "3201901234567" not in profile.tax_id_secret
    assert tax.tax_id_of(profile) == "3201901234567"
    services.save_tax_profile(aicha, city="Abomey-Calavi")
    profile.refresh_from_db()
    assert profile.city == "Abomey-Calavi" and tax.tax_id_of(profile) == "3201901234567"
    assert str(profile) == "Aïcha Hounkpè"
    empty = SellerTaxProfile(seller=aicha, legal_name="x")
    assert tax.tax_id_of(empty) == ""


def test_dac7_figures_per_seller_and_quarter():
    aicha = seller()
    services.save_tax_profile(
        aicha, legal_name="Aïcha H.", address="Rue 12", city="Cotonou", country="BJ", tax_id="99"
    )
    released = paid(sold_by=aicha)
    services.confirm_receipt(released, code_of(released), actor=aicha)
    partly = shipped(sold_by=aicha)
    dispute = services.open_dispute(partly, by=partly.buyer, reason="damaged")
    services.decide(dispute, actor=None, decision="partial", refund_minor=4_000)
    refunded = paid(sold_by=aicha)
    services.cancel(refunded, actor=refunded.buyer)
    payment(sold_by=aicha)  # never paid
    other = paid(sold_by=seller("Gloria Nails"))
    services.release(other, reason="test")

    year = timezone.now().year
    rows = {row["legal_name"]: row for row in tax.dac7_rows(year)}
    quarter = (timezone.now().month - 1) // 3 + 1
    hers = rows["Aïcha H."]
    assert hers[f"q{quarter}_amount_minor"] == 11_000 + 7_000
    assert hers[f"q{quarter}_sales"] == 2 and hers["tax_id"] == "99"
    assert rows[""][f"q{quarter}_sales"] == 1  # Gloria has no tax data yet
    assert tax.dac7_rows(year - 1) == []


def test_dates_of_dac7_follow_the_closing_day():
    p = paid()
    services.release(p, reason="test")
    Payment.objects.filter(pk=p.pk).update(
        released_at=timezone.now().replace(month=2, day=1) - datetime.timedelta(days=366)
    )
    year = timezone.now().year - 1
    assert tax.dac7_rows(year)[0]["q1_sales"] == 1
