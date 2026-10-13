"""Deadlines that act by themselves, and disputes from opening to decision."""

import datetime

import pytest
from django.contrib.auth.models import Group, Permission
from django.utils import timezone

from apps.core.tests.factories import PlatformSettingFactory
from apps.messaging.models import Conversation, Message
from apps.messaging.tests.factories import adult
from apps.notifications.models import Notification
from apps.payments import errors, services
from apps.payments.apps import DISPUTES_GROUP
from apps.payments.models import Dispute, DisputeEvidence, Payment, Payout, Refund
from apps.payments.services import automation, disputes
from apps.pros.models import ProProfile

from .factories import balances, code_of, commission, paid, payment, picture, seller, shipped

pytestmark = pytest.mark.django_db
S = Payment.Status
D = Dispute.Decision


def days(n):
    return timezone.now() + datetime.timedelta(days=n)


def status(p):
    p.refresh_from_db()
    return p.status


# --- Automatic steps -----------------------------------------------------------------------------


def test_unpaid_orders_expire():
    p = payment()
    assert automation.expire_unpaid() == 0
    assert automation.expire_unpaid(days(1)) == 1
    assert status(p) == S.CANCELLED and p.end_reason == "expired"
    assert automation.expire_unpaid(days(1)) == 0


def test_seller_reminded_then_order_cancelled_if_not_shipped():
    p = paid()
    service = paid(delivery_mode=Payment.Delivery.SERVICE, delivery_minor=0)
    assert automation.remind_shipping() == 0
    assert automation.remind_shipping(days(2.1)) == 1
    assert automation.remind_shipping(days(2.1)) == 0
    assert Notification.objects.filter(user=p.seller, event_key="payments.ship_reminder").exists()
    assert automation.cancel_unshipped(days(2)) == 0
    assert automation.cancel_unshipped(days(3.1)) == 1
    assert status(p) == S.REFUNDED and p.end_reason == "not_shipped"
    assert status(service) == S.HELD  # a deposit is not shipped
    assert balances(p)["seller_pending"] == 0


def test_delivered_without_code_reminders_then_release():
    commission(500)
    p = shipped()
    services.mark_delivered(p, actor=p.seller, proof_media_id=picture(p.seller).pk)
    assert automation.remind_release(days(1)) == 0
    assert automation.remind_release(days(2.1)) == 1
    assert automation.remind_release(days(2.1)) == 0
    assert automation.remind_release(days(5.1)) == 1
    assert automation.remind_release(days(6)) == 0
    assert (
        Notification.objects.filter(user=p.buyer, event_key="payments.release_reminder").count()
        == 2
    )
    assert automation.auto_release(days(6)) == 0
    assert automation.auto_release(days(7.1)) == 1
    assert status(p) == S.RELEASED and p.end_reason == "automatic"
    assert balances(p)["seller_available"] == 10_500


def test_deposit_released_after_the_appointment():
    p = paid(
        delivery_mode=Payment.Delivery.SERVICE,
        delivery_minor=0,
        purpose="deposit",
        service_at=days(1),
    )
    assert automation.auto_release(days(7)) == 0
    assert automation.auto_release(days(8.1)) == 1
    assert status(p) == S.RELEASED


def test_no_code_and_no_proof_opens_a_dispute():
    p = shipped()
    assert automation.auto_dispute(days(11)) == 0  # 5 days expected + 7
    assert automation.auto_dispute(days(12.1)) == 1
    assert status(p) == S.DISPUTED
    assert p.dispute.reason == Dispute.Reason.NO_PROOF and p.dispute.opened_by is None


def test_a_payment_that_changed_meanwhile_is_skipped(monkeypatch):
    p = paid()

    def busy(*args, **kwargs):
        raise errors.InvalidTransition()

    monkeypatch.setattr(automation.payment_services, "refund_full", busy)
    assert automation.cancel_unshipped(days(4)) == 0
    assert status(p) == S.HELD


def test_stuck_refunds_and_payouts_are_tried_again(monkeypatch):
    tried = []
    monkeypatch.setattr("apps.payments.tasks.run_refund.delay", tried.append)
    monkeypatch.setattr("apps.payments.tasks.run_payout.delay", tried.append)
    p = paid()
    refund = Refund.objects.create(payment=p, amount_minor=1, currency="XOF", reason="x")
    payout = Payout.objects.create(
        seller=p.seller, amount_minor=1, currency="XOF", provider="fake", destination="x"
    )
    later = timezone.now() + datetime.timedelta(minutes=11)
    assert automation.retry_stuck(later) == {"refunds": 1, "payouts": 1}
    assert tried == [str(refund.pk), str(payout.pk)]


def test_everything_together_runs_twice_without_effect_twice():
    p = paid()
    first = automation.run_all(days(4))
    second = automation.run_all(days(4))
    assert first["not_shipped"] == 1 and second["not_shipped"] == 0
    assert status(p) == S.REFUNDED


def test_the_periodic_task():
    from apps.payments.tasks import run_deadlines

    assert set(run_deadlines()) >= {"expired", "released", "disputes"}


# --- Disputes ------------------------------------------------------------------------------------


@pytest.fixture
def team():
    agent = adult("Solange")
    group = Group.objects.get(name=DISPUTES_GROUP)
    agent.groups.add(group)
    return agent


def test_a_client_opens_a_dispute_with_evidence(team):
    p = shipped()
    photo = picture(p.buyer, purpose="dispute_evidence")
    dispute = services.open_dispute(
        p, by=p.buyer, reason="damaged", description="Perruque abîmée", media_ids=[photo.pk]
    )
    assert status(p) == S.DISPUTED and p.disputed_at
    room = dispute.conversation
    assert room.purpose == Conversation.Purpose.DISPUTE and room.context_id == dispute.pk
    assert set(room.members.values_list("user_id", flat=True)) == {
        p.buyer_id,
        p.seller_id,
        team.pk,
    }
    assert Message.objects.filter(conversation=room, kind="system").exists()
    assert DisputeEvidence.objects.filter(dispute=dispute).count() == 2
    assert Notification.objects.filter(user=p.seller, event_key="disputes.opened").exists()
    assert str(dispute).startswith(p.reference)
    # Money frozen: still pending for the seller.
    assert balances(p)["seller_pending"] == 11_000


def test_who_and_when_a_dispute_can_be_opened():
    p = paid()
    with pytest.raises(errors.PaymentNotFound):
        services.open_dispute(p, by=p.seller, reason="damaged")
    with pytest.raises(errors.InvalidMedia):
        services.open_dispute(
            p, by=p.buyer, reason="damaged", media_ids=[picture(p.seller, "dispute_evidence").pk]
        )
    with pytest.raises(errors.DisputeNotAllowed):
        services.open_dispute(payment(), by=None, reason="damaged")


def test_evidence_from_both_sides_and_the_team(team):
    p = shipped()
    dispute = services.open_dispute(p, by=p.buyer, reason="not_received")
    services.add_evidence(dispute, author=p.seller, text="Suivi Gozem : livré le 12")
    services.add_evidence(
        dispute,
        author=p.seller,
        text="Photo de la remise",
        media_id=picture(p.seller, "dispute_evidence").pk,
    )
    team.user_permissions.add(Permission.objects.get(codename="decide_dispute"))
    team = type(team).objects.get(pk=team.pk)
    services.add_evidence(dispute, author=team, text="Appel passé à la cliente")
    with pytest.raises(errors.PaymentNotFound):
        services.add_evidence(dispute, author=adult("Zoé"), text="Je sais tout")
    with pytest.raises(errors.InvalidMedia):
        services.add_evidence(dispute, author=p.buyer, text="  ")
    assert dispute.evidence.count() == 3
    assert str(dispute.evidence.first()).startswith(p.reference)


@pytest.mark.parametrize(
    ("decision", "amount", "status_after", "refunded"),
    [
        (D.RELEASE, 0, S.RELEASED, 0),
        (D.REFUND, 0, S.REFUNDED, 11_330),
        (D.PARTIAL, 4_000, S.PARTIALLY_REFUNDED, 4_000),
    ],
)
def test_one_click_decisions(team, decision, amount, status_after, refunded):
    p = shipped()
    dispute = services.open_dispute(p, by=p.buyer, reason="not_as_described")
    services.decide(dispute, actor=team, decision=decision, refund_minor=amount, note="Vu.")
    dispute.refresh_from_db()
    assert status(p) == status_after and dispute.refund_minor == refunded
    assert dispute.status == Dispute.Status.DECIDED and dispute.decided_by == team
    assert Conversation.objects.get(pk=dispute.conversation_id).is_closed
    assert Notification.objects.filter(user=p.buyer, event_key="disputes.decided").exists()
    with pytest.raises(errors.AlreadyDecided):
        services.decide(dispute, actor=team, decision=D.RELEASE)
    with pytest.raises(errors.AlreadyDecided):
        services.add_evidence(dispute, author=p.buyer, text="Encore")


def test_an_unknown_decision_is_refused(team):
    p = shipped()
    dispute = services.open_dispute(p, by=p.buyer, reason="other")
    with pytest.raises(errors.InvalidTransition):
        services.decide(dispute, actor=team, decision="maybe")


def test_a_seller_losing_too_many_disputes_is_suspended(team):
    PlatformSettingFactory(key="payments.lost_disputes_threshold", value="2")
    aicha = seller()
    for _ in range(2):
        p = shipped(sold_by=aicha)
        dispute = services.open_dispute(p, by=p.buyer, reason="not_received")
        services.decide(dispute, actor=team, decision=D.REFUND)
    pro = ProProfile.objects.get(user=aicha)
    assert pro.status == ProProfile.Status.SUSPENDED and "2" in pro.suspension_reason
    # Already suspended, a client without showcase, a winner: nothing more.
    assert disputes.check_seller(aicha) is False
    assert disputes.check_seller(adult("Inès")) is False
    other = seller("Gloria Nails")
    assert disputes.check_seller(other) is False


def test_a_client_selling_without_showcase_is_not_suspended(team):
    PlatformSettingFactory(key="payments.lost_disputes_threshold", value="1")
    ines = adult("Inès")
    p = shipped(sold_by=ines)
    dispute = services.open_dispute(p, by=p.buyer, reason="not_received")
    services.decide(dispute, actor=team, decision=D.REFUND)
    assert disputes.check_seller(ines) is False


def test_dispute_reminder_halfway_then_first_in_the_queue():
    p = shipped()
    dispute = services.open_dispute(p, by=p.buyer, reason="not_received")
    now = timezone.now()
    assert disputes.follow_deadlines(now) == {"reminded": 0, "overdue": 0}
    halfway = now + datetime.timedelta(hours=25)
    assert disputes.follow_deadlines(halfway) == {"reminded": 1, "overdue": 0}
    late = now + datetime.timedelta(hours=49)
    assert disputes.follow_deadlines(late) == {"reminded": 0, "overdue": 1}
    dispute.refresh_from_db()
    assert dispute.overdue and dispute.reminded_at
    assert Notification.objects.filter(user=p.seller, event_key="disputes.reminder").exists()


def test_without_dispute_team_the_room_has_the_two_parties():
    p = shipped()
    dispute = services.open_dispute(p, by=p.buyer, reason="not_received")
    assert dispute.conversation.members.count() == 2
    Group.objects.filter(name=DISPUTES_GROUP).delete()
    assert disputes.dispute_team() == []


def test_receipt_code_still_works_until_a_dispute():
    p = shipped()
    services.open_dispute(p, by=p.buyer, reason="not_received")
    with pytest.raises(errors.InvalidTransition):
        services.confirm_receipt(p, code_of(p), actor=p.seller)


def test_a_picture_as_evidence_without_words_and_a_decision_without_room(team):
    p = shipped()
    dispute = services.open_dispute(p, by=p.buyer, reason="damaged")
    evidence = services.add_evidence(
        dispute, author=p.buyer, media_id=picture(p.buyer, "dispute_evidence").pk
    )
    assert evidence.text == "" and evidence.media_id
    Dispute.objects.filter(pk=dispute.pk).update(conversation=None)
    dispute.refresh_from_db()
    services.decide(dispute, actor=team, decision=D.RELEASE)
    assert status(p) == S.RELEASED
