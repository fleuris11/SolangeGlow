"""Disputes: money frozen, a room for three, evidence, a decision, sanctions of sellers."""

from __future__ import annotations

import datetime

from django.conf import settings
from django.contrib.auth.models import Group
from django.db import transaction
from django.utils import timezone, translation
from django.utils.translation import gettext

from apps.core.audit.services import record
from apps.core.media.models import MediaAsset
from apps.core.selectors import get_setting
from apps.notifications.services import notify

from .. import errors
from ..apps import DISPUTES_GROUP as DISPUTE_GROUP
from ..models import Dispute, DisputeEvidence, Payment
from .common import S, locked, move
from .payments import money, refund_full, refund_partial, release

D = Dispute.Decision


def dispute_team():
    """People of the « Disputes » group: they join every dispute room."""
    group = Group.objects.filter(name=DISPUTE_GROUP).first()
    return list(group.user_set.filter(is_active=True)) if group else []


def _hours(payment: Payment) -> int:
    return int(get_setting("escrow.dispute_response_hours", country=payment.country, default=48))


def _notify_both(dispute: Dispute, event: str, context: dict | None = None) -> None:
    payment = dispute.payment
    for person in (payment.buyer, payment.seller):
        notify(
            person,
            event,
            {"reference": payment.reference, **(context or {})},
            link=f"/payments/{payment.pk}",
        )


def open_dispute(
    payment: Payment,
    *,
    by=None,
    reason: str,
    description: str = "",
    media_ids=(),
) -> Dispute:
    """By the client (not received, not as described…) or by the platform (no proof)."""
    from apps.messaging import services as messaging

    with transaction.atomic():
        payment = locked(payment)
        if by is not None and payment.buyer_id != by.pk:
            raise errors.PaymentNotFound()
        if payment.status not in (S.HELD, S.SHIPPED):
            raise errors.DisputeNotAllowed()
        move(payment, S.DISPUTED, actor=by, reason=reason)
        dispute = Dispute.objects.create(
            payment=payment,
            opened_by=by,
            reason=reason,
            description=description.strip()[:4000],
            response_due_at=timezone.now() + datetime.timedelta(hours=_hours(payment)),
        )
        with translation.override(settings.LANGUAGE_CODE):
            title = gettext("Dispute %(reference)s") % {"reference": payment.reference}
            summary = gettext(
                "Dispute opened: %(reason)s. The money is frozen. Each side adds its "
                "evidence; the Solange Glow team decides."
            ) % {"reason": dispute.get_reason_display()}
        room = messaging.create_group(
            None,
            [payment.buyer, payment.seller],
            title=title,
            purpose="dispute",
            context_type="dispute",
            context_id=dispute.pk,
            staff=dispute_team(),
        )
        messaging.send_system(room, summary)
        dispute.conversation = room
        dispute.save(update_fields=["conversation", "updated_at"])
        if description.strip():
            DisputeEvidence.objects.create(
                dispute=dispute, author=by, text=description.strip()[:4000]
            )
        for media_id in media_ids:
            _attach(dispute, by, media_id)
        record("payments.dispute_opened", dispute, actor=by, metadata={"reason": reason})
        transaction.on_commit(
            lambda: _notify_both(dispute, "disputes.opened", {"hours": _hours(payment)})
        )
    return dispute


def _attach(dispute: Dispute, author, media_id) -> DisputeEvidence:
    media = MediaAsset.objects.filter(pk=media_id, owner=author, purpose="dispute_evidence").first()
    if media is None or not media.is_ready:
        raise errors.InvalidMedia()
    return DisputeEvidence.objects.create(dispute=dispute, author=author, media=media)


def _party(dispute: Dispute, user) -> bool:
    payment = dispute.payment
    if user.pk in (payment.buyer_id, payment.seller_id):
        return True
    return user.has_perm("payments.decide_dispute")


@transaction.atomic
def add_evidence(dispute: Dispute, *, author, text: str = "", media_id=None) -> DisputeEvidence:
    if not _party(dispute, author):
        raise errors.PaymentNotFound()
    if dispute.status != Dispute.Status.OPEN:
        raise errors.AlreadyDecided()
    if media_id:
        evidence = _attach(dispute, author, media_id)
        if text.strip():
            evidence.text = text.strip()[:4000]
            evidence.save(update_fields=["text", "updated_at"])
    else:
        if not text.strip():
            raise errors.InvalidMedia()
        evidence = DisputeEvidence.objects.create(
            dispute=dispute, author=author, text=text.strip()[:4000]
        )
    record("payments.dispute_evidence", dispute, actor=author)
    return evidence


def decide(
    dispute: Dispute, *, actor, decision: str, refund_minor: int = 0, note: str = ""
) -> Dispute:
    """One click in the admin: pay the seller, refund everything, or refund part."""
    from apps.messaging import services as messaging

    with transaction.atomic():
        dispute = Dispute.objects.select_for_update().select_related("payment").get(pk=dispute.pk)
        if dispute.status != Dispute.Status.OPEN:
            raise errors.AlreadyDecided()
        payment = dispute.payment
        if decision == D.RELEASE:
            release(payment, actor=actor, reason="dispute_release")
        elif decision == D.REFUND:
            refund_full(payment, actor=actor, reason="dispute_refund")
        elif decision == D.PARTIAL:
            refund_partial(payment, refund_minor, actor=actor, reason="dispute_partial")
        else:
            raise errors.InvalidTransition()
        payment.refresh_from_db()
        dispute.status = Dispute.Status.DECIDED
        dispute.decision = decision
        dispute.refund_minor = payment.refunded_minor
        dispute.decided_by = actor
        dispute.decided_at = timezone.now()
        dispute.note = note.strip()[:4000]
        dispute.save()
        record(
            "payments.dispute_decided",
            dispute,
            actor=actor,
            metadata={"decision": decision, "refund_minor": dispute.refund_minor},
        )
        if dispute.conversation_id:
            with translation.override(settings.LANGUAGE_CODE):
                text = gettext("Decision: %(decision)s.") % {
                    "decision": dispute.get_decision_display()
                }
            messaging.send_system(dispute.conversation, f"{text} {dispute.note}".strip())
            type(dispute.conversation).objects.filter(pk=dispute.conversation_id).update(
                is_closed=True
            )
        refunded = money(dispute.refund_minor, payment.currency)
        transaction.on_commit(
            lambda: _notify_both(
                dispute,
                "disputes.decided",
                {"decision": dispute.get_decision_display(), "refunded": refunded},
            )
        )
        if decision in (D.REFUND, D.PARTIAL):
            check_seller(payment.seller)
    return dispute


def lost_disputes(seller, *, since) -> int:
    return Dispute.objects.filter(
        payment__seller=seller,
        decision__in=[D.REFUND, D.PARTIAL],
        decided_at__gte=since,
    ).count()


def check_seller(seller) -> bool:
    """Too many lost disputes in the window: the showcase is suspended automatically."""
    from apps.pros import services as pros
    from apps.pros.models import ProProfile

    threshold = int(get_setting("payments.lost_disputes_threshold", default=3))
    days = int(get_setting("payments.lost_disputes_window_days", default=90))
    since = timezone.now() - datetime.timedelta(days=days)
    if lost_disputes(seller, since=since) < threshold:
        return False
    pro = ProProfile.objects.filter(user=seller).first()  # fresh: never twice
    if pro is None or pro.status == ProProfile.Status.SUSPENDED:
        return False
    with translation.override(seller.preferred_language or settings.LANGUAGE_CODE):
        reason = gettext("Too many disputes lost (%(count)s in %(days)s days).") % {
            "count": threshold,
            "days": days,
        }
    pros.suspend(pro, actor=None, reason=reason)
    return True


def follow_deadlines(now=None) -> dict:
    """Reminder halfway; deadline passed: the dispute goes first in the team's queue."""
    now = now or timezone.now()
    counts = {"reminded": 0, "overdue": 0}
    with transaction.atomic():
        waiting = Dispute.objects.select_for_update(skip_locked=True).filter(
            status=Dispute.Status.OPEN, reminded_at__isnull=True
        )
        for dispute in waiting.select_related("payment"):
            half = datetime.timedelta(hours=_hours(dispute.payment) / 2)
            if now < dispute.response_due_at - half:
                continue
            dispute.reminded_at = now
            dispute.save(update_fields=["reminded_at", "updated_at"])
            transaction.on_commit(lambda d=dispute: _notify_both(d, "disputes.reminder"))
            counts["reminded"] += 1
    counts["overdue"] = Dispute.objects.filter(
        status=Dispute.Status.OPEN, overdue=False, response_due_at__lte=now
    ).update(overdue=True)
    return counts
