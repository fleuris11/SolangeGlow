"""Using a gift in Benin: opening it, booking the offered service (with or without an
account), receiving the offered product, paying with a Glow gift card. Each use is a
payment in FCFA paid by the gift; a refund puts the money back onto it."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext, override

from apps.core.audit.services import record
from apps.notifications.services import notify
from apps.payments import services as payment_services
from apps.payments.models import Payment, PaymentGroup, Purpose
from apps.payments.providers import ProviderError

from .. import errors
from ..models import Gift, GiftCredit, GiftUse
from . import common, offering

G = Gift.Status
PS = Payment.Status
K = Gift.Kind


def by_token(token: str) -> Gift:
    gift = (
        Gift.objects.select_related("giver", "pro", "service", "variant__product", "payment")
        .filter(token=token or "")
        .exclude(status__in=(G.WAITING_PAYMENT, G.CANCELLED))
        .first()
    )
    if gift is None:
        raise errors.GiftNotFound()
    return gift


def is_giver(gift: Gift, viewer) -> bool:
    return viewer is not None and viewer.is_authenticated and viewer.pk == gift.giver_id


def open_gift(gift: Gift, viewer=None) -> Gift:
    """The person opens her link: the giver is told once (her own look is only a preview)."""
    if gift.status == G.SCHEDULED or is_giver(gift, viewer):
        return gift
    with transaction.atomic():
        gift = common.locked(gift)
        fields = []
        if (
            viewer is not None
            and viewer.is_authenticated
            and gift.recipient_user_id is None
            and str(viewer.phone or "") == gift.recipient_phone
        ):
            gift.recipient_user = viewer
            fields.append("recipient_user")
        first = gift.status == G.SENT
        if first:
            gift.status = G.OPENED
            gift.opened_at = timezone.now()
            fields += ["status", "opened_at"]
        if fields:
            gift.save(update_fields=[*fields, "updated_at"])
    if first:
        common.after_commit(
            lambda: notify(
                gift.giver,
                "gifts.opened",
                {"name": gift.recipient_name, "what": gift.title},
                link=f"/cadeaux/{gift.pk}",
            )
        )
    return by_token(gift.token)


def claim(gift: Gift, user) -> Gift:
    """A Glow gift card kept in « My gifts » (the code works without it too)."""
    if is_giver(gift, user):
        raise errors.GiverCannotDoThis()
    if gift.kind != K.CARD or not common.usable(gift):
        raise errors.WrongKind()
    if gift.recipient_user_id not in (None, user.pk):
        raise errors.GiftNotFound()
    Gift.objects.filter(pk=gift.pk).update(recipient_user=user)
    gift.recipient_user = user
    open_gift(gift, user)
    return gift


def _check_ready(gift: Gift, kind: str | tuple) -> None:
    kinds = (kind,) if isinstance(kind, str) else kind
    if gift.kind not in kinds:
        raise errors.WrongKind()
    if gift.status == G.SCHEDULED:
        raise errors.NotOpenYet(details={"date": timezone.localtime(gift.send_at).date()})
    if not common.usable(gift):
        raise errors.GiftNotFound()


def _spend(
    gift: Gift,
    payment: Payment,
    *,
    label: str,
    source_type: str,
    source_id,
    tell_buyer: bool,
    group: PaymentGroup | None = None,
) -> None:
    """The gift pays (all of) this payment, or every payment of a cart."""
    gift = common.locked(gift)
    payments = list(group.payments.all()) if group is not None else [payment]
    total = sum(p.total_minor for p in payments)
    if not common.usable(gift):
        raise errors.GiftNotFound()
    if any(p.currency != gift.currency for p in payments):
        raise errors.CardOnlyHere()
    if total > gift.balance_minor:
        raise errors.NotEnoughLeft(
            details={"balance": common.money(gift.balance_minor, gift.currency)}
        )
    first = not gift.uses.exists()
    for member in payments:
        GiftUse.objects.create(
            gift=gift,
            payment=member,
            amount_minor=member.total_minor,
            label=label[:200],
            source_type=source_type if group is None else member.source_type,
            source_id=source_id if group is None else member.source_id,
        )
    gift.balance_minor -= total
    gift.status = G.USED
    gift.save(update_fields=["balance_minor", "status", "updated_at"])
    key = f"gift:{gift.pk}:{(group or payment).pk}"
    if group is not None:
        payment_services.pay_group_from_gift(group, key=key)
    else:
        payment_services.pay_from_gift(payment, key=key, tell_buyer=tell_buyer)
    if first:
        offering.release_euros(gift, "gift_used")
        common.after_commit(
            lambda: notify(
                gift.giver,
                "gifts.used",
                {"name": gift.recipient_name, "what": label},
                link=f"/cadeaux/{gift.pk}",
            )
        )
    record("gifts.used", gift, metadata={"amount": total, "for": source_type})


def _unused(gift: Gift) -> None:
    """An offered service or product is used whole: once (again after a refund)."""
    if gift.balance_minor != gift.value_minor:
        raise errors.AlreadyUsed()


# --- The offered service -------------------------------------------------------------------------


@transaction.atomic
def book(
    gift: Gift,
    start,
    *,
    viewer=None,
    staff_id=None,
    guest_name: str = "",
    guest_phone: str = "",
    note: str = "",
):
    """The person (or the giver, for her) books the offered service: already paid."""
    from apps.booking.services import appointments

    gift = common.locked(gift)
    _check_ready(gift, K.SERVICE)
    _unused(gift)
    user = viewer if viewer is not None and viewer.is_authenticated else None
    if user is not None and user.pk == gift.giver_id:
        # The giver books for her: the appointment is in the name of the person.
        user, guest_name, guest_phone = None, gift.recipient_name, gift.recipient_phone
    elif user is None:
        guest_name = guest_name or gift.recipient_name
        guest_phone = guest_phone or gift.recipient_phone
    with override(gift.giver.preferred_language or "fr"):
        label = gettext("%(service)s at %(pro)s") % {
            "service": gift.service.name,
            "pro": gift.pro.display_name,
        }

    def prepay(appointment):
        payment = payment_services.create_payment(
            gift.giver,
            gift.pro.user,
            purpose=Purpose.DEPOSIT,
            items_minor=gift.balance_minor,
            currency=gift.currency,
            description=f"{gift.service.name} — {gift.pro.display_name}"[:200],
            delivery_mode=Payment.Delivery.SERVICE,
            source_type="booking",
            source_id=appointment.pk,
            service_at=appointment.starts_at,
            with_buyer_fee=False,
        )
        _spend(
            gift,
            payment,
            label=label,
            source_type="booking",
            source_id=appointment.pk,
            tell_buyer=False,
        )
        return Payment.objects.get(pk=payment.pk)

    appointment = appointments.book(
        gift.pro,
        gift.service_id,
        start,
        user=user,
        guest_name=guest_name,
        guest_phone=guest_phone,
        staff_id=staff_id,
        note=note or gettext("Gift from %(name)s") % {"name": gift.from_name},
        prepaid_minor=gift.balance_minor,
        prepay=prepay,
    )
    return appointment


# --- The offered product -------------------------------------------------------------------------


@transaction.atomic
def receive(
    gift: Gift,
    *,
    viewer=None,
    address: str = "",
    landmarks: str = "",
    phone: str = "",
    pickup_point_id=None,
):
    """The person confirms where she receives the product: the order leaves now."""
    from apps.selection_france import services as selection
    from apps.shop.services import checkout

    gift = common.locked(gift)
    _check_ready(gift, (K.PRODUCT, K.SELECTION))
    _unused(gift)
    note = gettext("Gift from %(name)s for %(to)s") % {
        "name": gift.from_name,
        "to": gift.recipient_name,
    }
    if gift.kind == K.PRODUCT:
        order = checkout.place_gift_order(
            gift.giver,
            gift.variant_id,
            quantity=gift.quantity,
            items_minor=gift.balance_minor - gift.delivery_minor,
            delivery_mode=gift.delivery_mode,
            zone_id=gift.zone_id,
            delivery_minor=gift.delivery_minor,
            address=address,
            landmarks=landmarks,
            phone=phone or gift.recipient_phone,
            note=note,
        )
        source = "order"
    else:
        order = selection.place_gift_order(
            gift.giver,
            gift.selection_product_id,
            pickup_point_id=pickup_point_id,
            unit_price=gift.balance_minor,
            option=gift.option,
        )
        source = "selection"
    _spend(
        gift,
        order.payment,
        label=gift.title,
        source_type=source,
        source_id=order.pk,
        tell_buyer=False,
    )
    return order


@transaction.atomic
def as_card(gift: Gift, *, viewer=None) -> Gift:
    """The offered thing is not available any more: the gift becomes a Glow gift card."""
    if is_giver(gift, viewer):
        raise errors.GiverCannotDoThis()
    gift = common.locked(gift)
    _check_ready(gift, (K.SERVICE, K.PRODUCT, K.SELECTION))
    _unused(gift)
    gift.kind = K.CARD
    gift.title = gettext("Glow gift card")
    gift.save(update_fields=["kind", "title", "updated_at"])
    record("gifts.as_card", gift, actor=viewer if viewer and viewer.is_authenticated else None)
    return gift


# --- The Glow gift card --------------------------------------------------------------------------


def card_by_code(code: str) -> Gift | None:
    clean = (code or "").strip().upper().replace(" ", "").replace("-", "")
    if not clean:
        return None
    return Gift.objects.filter(code=clean, kind=K.CARD).first()


@transaction.atomic
def pay_with_card(code: str, *, user, payment_id=None, group_id=None) -> Gift:
    """A purchase in Benin (order, cart, training, France Selection…) paid by the card."""
    card = card_by_code(code)
    if card is None or not common.usable(card) or card.giver_id == user.pk:
        raise errors.GiftNotFound()
    if group_id:
        group = PaymentGroup.objects.filter(pk=group_id, buyer=user, paid_at__isnull=True).first()
        if group is None:
            raise errors.GiftNotFound()
        first = group.payments.order_by("created_at").first()
        if first is None:
            raise errors.GiftNotFound()
        _spend(
            card,
            first,
            label=gettext("Order %(reference)s") % {"reference": group.reference},
            source_type="",
            source_id=None,
            tell_buyer=True,
            group=group,
        )
    else:
        payment = Payment.objects.filter(
            pk=payment_id, buyer=user, status=PS.PENDING_PAYMENT, group__isnull=True
        ).first()
        if payment is None:
            raise errors.GiftNotFound()
        _spend(
            card,
            payment,
            label=payment.description,
            source_type=payment.source_type,
            source_id=payment.source_id,
            tell_buyer=True,
        )
    if card.recipient_user_id is None:
        Gift.objects.filter(pk=card.pk).update(recipient_user=user)
    card.refresh_from_db()
    return card


def cover_deposit(appointment, code: str, actor) -> bool:
    """A booking deposit paid with a Glow gift card (the code field of the booking)."""
    card = card_by_code(code)
    if card is None or actor is None or card.giver_id == actor.pk:
        return False
    payment = payment_services.create_payment(
        actor,
        appointment.pro.user,
        purpose=Purpose.DEPOSIT,
        items_minor=appointment.deposit_minor,
        currency=appointment.currency,
        description=f"{appointment.service.name} — {appointment.pro.display_name}"[:200],
        delivery_mode=Payment.Delivery.SERVICE,
        source_type="booking",
        source_id=appointment.pk,
        service_at=appointment.starts_at,
    )
    try:
        with transaction.atomic():
            _spend(
                card,
                payment,
                label=payment.description,
                source_type="booking",
                source_id=appointment.pk,
                tell_buyer=True,
            )
    except (errors.GiftNotFound, errors.NotEnoughLeft, errors.CardOnlyHere):
        payment_services.mark_not_paid(payment, reason="gift_card_refused")
        return False
    appointment.payment = Payment.objects.get(pk=payment.pk)
    appointment.save(update_fields=["payment", "updated_at"])
    return True


# --- Refunds come back onto the gift ------------------------------------------------------------


def credit_back(payment: Payment, refund) -> None:
    """Called by the internal provider « gift » for each refund (once per refund)."""
    with transaction.atomic():
        use = GiftUse.objects.select_for_update().filter(payment=payment).first()
        if use is None:
            raise ProviderError("This payment was not paid by a gift")
        _credit, created = GiftCredit.objects.get_or_create(
            refund=refund, defaults={"use": use, "amount_minor": refund.amount_minor}
        )
        if not created:
            return
        use.refunded_minor += refund.amount_minor
        use.save(update_fields=["refunded_minor", "updated_at"])
        gift = common.locked(use.gift)
        gift.balance_minor += refund.amount_minor
        if gift.status == G.USED and gift.balance_minor >= gift.value_minor:
            gift.status = G.OPENED
        gift.save(update_fields=["balance_minor", "status", "updated_at"])
        record("gifts.credited", gift, metadata={"amount": refund.amount_minor})
