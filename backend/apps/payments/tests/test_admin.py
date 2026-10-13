"""Finance console: dashboard, exports, one-click decisions, refunds closed by hand."""

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.core.audit.models import AuditEvent
from apps.payments import services
from apps.payments.apps import DISPUTES_GROUP, FINANCE_GROUP
from apps.payments.models import Dispute, Payment, PricingRule, Refund

from .factories import code_of, paid, shipped

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client):
    client.force_login(UserFactory(is_staff=True, is_superuser=True, email="boss@example.com"))
    return client


def staff_in(group_name, client):
    user = UserFactory(is_staff=True, email=f"{group_name.lower()}@example.com")
    user.groups.add(Group.objects.get(name=group_name))
    client.force_login(user)
    return client


def test_dashboard_lists_and_details(admin_client):
    p = paid()
    services.confirm_receipt(p, code_of(p), actor=p.seller)
    page = admin_client.get(reverse("admin:payments_finance"))
    content = page.content.decode()
    assert page.status_code == 200 and "XOF" in content and "330" in content
    for name in (
        "payment",
        "journalentry",
        "ledgeraccount",
        "refund",
        "payout",
        "dispute",
        "pricingrule",
        "sellertaxprofile",
        "reconciliationrun",
        "webhookevent",
    ):
        assert admin_client.get(reverse(f"admin:payments_{name}_changelist")).status_code == 200
    detail = admin_client.get(reverse("admin:payments_payment_change", args=[p.pk]))
    assert detail.status_code == 200 and "payment.released" in detail.content.decode()


@pytest.mark.parametrize("what", ["payments", "ledger", "payouts", "dac7"])
def test_csv_exports_are_traced(admin_client, what):
    p = paid()
    services.release(p, reason="test")
    response = admin_client.get(reverse("admin:payments_export", args=[what]), {"year": 2026})
    assert response.status_code == 200 and response["Content-Type"].startswith("text/csv")
    assert AuditEvent.objects.filter(action="payments.export").exists()


def test_unknown_export_and_dac7_only_for_finance(client):
    finance = staff_in(FINANCE_GROUP, client)
    assert finance.get(reverse("admin:payments_export", args=["dac7"])).status_code == 200
    assert finance.get(reverse("admin:payments_export", args=["secrets"])).status_code == 403
    disputes = staff_in(DISPUTES_GROUP, client)
    assert disputes.get(reverse("admin:payments_export", args=["dac7"])).status_code == 403
    assert disputes.get(reverse("admin:payments_finance")).status_code == 200


def test_dispute_decisions_in_one_click(client):
    disputes = staff_in(DISPUTES_GROUP, client)
    p = shipped()
    dispute = services.open_dispute(p, by=p.buyer, reason="not_received")
    page = disputes.get(reverse("admin:payments_dispute_change", args=[dispute.pk]))
    assert page.status_code == 200
    form = disputes.get(reverse("admin:payments_dispute_partial_detail", args=[dispute.pk]))
    assert form.status_code == 200
    response = disputes.post(
        reverse("admin:payments_dispute_partial_detail", args=[dispute.pk]),
        {"refund_minor": 4_000, "note": "Moitié"},
    )
    assert response.status_code == 302
    dispute.refresh_from_db()
    assert dispute.decision == "partial" and dispute.refund_minor == 4_000
    again = disputes.get(reverse("admin:payments_dispute_release_detail", args=[dispute.pk]))
    assert again.status_code == 302  # already decided: a message, nothing moves
    assert Payment.objects.get(pk=p.pk).status == "partially_refunded"


@pytest.mark.parametrize(("action", "status"), [("release", "released"), ("refund", "refunded")])
def test_release_or_refund_buttons(admin_client, action, status):
    p = shipped()
    dispute = services.open_dispute(p, by=p.buyer, reason="not_received")
    admin_client.get(reverse(f"admin:payments_dispute_{action}_detail", args=[dispute.pk]))
    assert Payment.objects.get(pk=p.pk).status == status


def test_refunds_closed_by_hand(admin_client):
    p = paid()
    services.cancel(p, actor=p.buyer)
    refund = Refund.objects.get(payment=p)
    Refund.objects.filter(pk=refund.pk).update(status=Refund.Status.MANUAL)
    admin_client.post(
        reverse("admin:payments_refund_changelist"),
        {"action": "mark_done", "_selected_action": [str(refund.pk)]},
    )
    assert Refund.objects.get(pk=refund.pk).status == Refund.Status.SUCCEEDED


def test_pricing_rules_are_edited_and_traced(admin_client):
    response = admin_client.post(
        reverse("admin:payments_pricingrule_add"),
        {
            "kind": "commission",
            "name": "Commission 5 %",
            "is_active": "on",
            "percent_bps": 500,
            "fixed_minor": 0,
            "priority": 0,
        },
    )
    assert response.status_code == 302
    rule = PricingRule.objects.get(name="Commission 5 %")
    assert AuditEvent.objects.filter(action="admin.create", target_id=str(rule.pk)).exists()


def test_nobody_edits_payments_or_disputes_by_hand(admin_client):
    p = shipped()
    dispute = services.open_dispute(p, by=p.buyer, reason="damaged")
    response = admin_client.post(
        reverse("admin:payments_dispute_change", args=[dispute.pk]), {"decision": "refund"}
    )
    assert response.status_code == 403
    assert Dispute.objects.get(pk=dispute.pk).decision == ""
