"""Points given for what happens elsewhere: a post, a review, an appointment done, a
purchase (money released), the first purchase of a goddaughter."""

from __future__ import annotations

from apps.payments.models import Payment

from ..models import Action
from . import points, referrals, rewards
from .common import setting

DEFAULT_PURPOSES = ["order", "selection", "training", "package", "gift_card", "gift"]


def on_post_published(post) -> None:
    if post.visibility == "visible" and post.deleted_at is None:
        points.award(
            post.author, Action.POST, key=f"post:{post.pk}", source_type="post", source_id=post.pk
        )


def on_review_created(review) -> None:
    if review.visibility == "visible":
        points.award(
            review.author,
            Action.REVIEW,
            key=f"review:{review.pk}",
            source_type="review",
            source_id=review.pk,
        )


def on_appointment_completed(appointment) -> None:
    if appointment.client_id:
        points.award(
            appointment.client,
            Action.BOOKING,
            key=f"booking:{appointment.pk}",
            source_type="appointment",
            source_id=appointment.pk,
        )


def on_payment_moved(payment: Payment) -> None:
    status = payment.status
    if status == Payment.Status.RELEASED:
        if payment.purpose in (setting("glow.purchase_purposes", DEFAULT_PURPOSES) or []):
            points.award(
                payment.buyer,
                Action.PURCHASE,
                key=f"purchase:{payment.pk}",
                source_type="payment",
                source_id=payment.pk,
            )
        referrals.on_purchase(payment)
    elif status in (Payment.Status.CANCELLED, Payment.Status.REFUNDED):
        from apps.selection_france.models import SelectionOrder

        order_id = SelectionOrder.objects.filter(payment=payment).values_list("pk", flat=True)
        for pk in order_id:
            rewards.give_back(rewards.SELECTION, pk)
