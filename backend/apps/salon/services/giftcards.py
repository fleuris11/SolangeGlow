"""Gift cards of a salon (free, with a commission on the online sale).

Bought online: the money is held (secure payment) until the first use, then it goes to
the pro; a card never used gives its money to the pro when it expires. A card is used at
the salon (the pro types the code) or online for a booking deposit, only at the pro who
sold it.
"""

from __future__ import annotations

import datetime
import secrets

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext

from apps.core.audit.services import record
from apps.core.money import Money
from apps.notifications.services import notify, notify_contact, send_direct
from apps.payments import services as payment_services
from apps.payments.models import Payment, Purpose

from .. import errors
from ..models import GiftCard, GiftCardUse
from . import common, onsite

SOURCE = "salon_gift_card"
G = GiftCard.Status
PS = Payment.Status
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(10))


def _limits(pro) -> tuple[int, int]:
    code = pro.country.code if pro.country_id else "BJ"
    defaults = {"BJ": (5_000, 500_000), "FR": (1_000, 50_000)}.get(code, (1_000, 50_000))
    low, high = common.setting("salon.gift_card_limits", pro, list(defaults))
    return int(low), int(high)


def offer(pro) -> dict:
    """What the showcase shows to buy a gift card (amounts and suggestions)."""
    low, high = _limits(pro)
    steps = [low * 2, low * 4, low * 10] if low else []
    return {
        "pro_name": pro.display_name,
        "currency": pro.currency or "XOF",
        "min_minor": low,
        "max_minor": high,
        "suggestions": [v for v in steps if v <= high],
        "validity_days": int(common.setting("salon.gift_card_validity_days", pro, 365)),
    }


def _check_amount(pro, amount_minor) -> None:
    low, high = _limits(pro)
    if type(amount_minor) is not int or not low <= amount_minor <= high:
        currency = pro.currency or "XOF"
        raise errors.InvalidGiftCard(
            details={
                "min": Money(low, currency).format("fr"),
                "max": Money(high, currency).format("fr"),
            }
        )


def _create(pro, amount_minor: int, status: str, **values) -> GiftCard:
    days = int(common.setting("salon.gift_card_validity_days", pro, 365))
    for _attempt in range(5):
        try:
            with transaction.atomic():
                return GiftCard.objects.create(
                    pro=pro,
                    code=new_code(),
                    amount_minor=amount_minor,
                    balance_minor=amount_minor,
                    currency=pro.currency or "XOF",
                    expires_on=timezone.localdate() + datetime.timedelta(days=days),
                    status=status,
                    **values,
                )
        except IntegrityError:  # the same code twice: very unlikely, try another one
            continue
    raise RuntimeError("No free gift card code")


@transaction.atomic
def buy_online(
    buyer,
    pro,
    *,
    amount_minor: int,
    recipient_name: str,
    recipient_contact: str = "",
    message: str = "",
    from_name: str = "",
) -> tuple[GiftCard, Payment]:
    if not pro.is_published:
        raise errors.NotFound()
    _check_amount(pro, amount_minor)
    card = _create(
        pro,
        amount_minor,
        G.WAITING,
        buyer=buyer,
        from_name=(from_name or buyer.first_name or "")[:80],
        recipient_name=(recipient_name or "").strip()[:80] or "—",
        recipient_contact=(recipient_contact or "").strip()[:120],
        message=(message or "").strip()[:300],
    )
    payment = payment_services.create_payment(
        buyer,
        pro.user,
        purpose=Purpose.GIFT_CARD,
        items_minor=amount_minor,
        currency=card.currency,
        description=gettext("Gift card %(pro)s") % {"pro": pro.display_name},
        delivery_mode=Payment.Delivery.SERVICE,
        source_type=SOURCE,
        source_id=card.pk,
    )
    card.payment = payment
    card.save(update_fields=["payment", "updated_at"])
    return card, payment_services.start_checkout(payment, buyer=buyer)


@transaction.atomic
def sell_on_site(
    pro, *, amount_minor: int, method: str, actor, recipient_name: str = ""
) -> GiftCard:
    _check_amount(pro, amount_minor)
    card = _create(
        pro, amount_minor, G.ACTIVE, recipient_name=(recipient_name or "—")[:80], sold_on_site=True
    )
    onsite.record_payment(
        pro,
        amount_minor=amount_minor,
        method=method,
        actor=actor,
        label=gettext("Gift card %(code)s") % {"code": card.code},
    )
    record("salon.gift_card_sold", card, actor=actor)
    return card


def may_cancel_payment(payment: Payment, actor) -> bool:
    return True


def on_payment_change(payment: Payment) -> None:
    with transaction.atomic():
        card = GiftCard.objects.select_for_update().filter(payment=payment).first()
        if card is None:
            return
        if payment.status == PS.HELD and card.status == G.WAITING:
            card.status = G.ACTIVE
            card.sent_at = timezone.now()
            card.save(update_fields=["status", "sent_at", "updated_at"])
            transaction.on_commit(lambda: _send(card))
        elif payment.status == PS.CANCELLED and card.status == G.WAITING:
            card.status = G.CANCELLED
            card.save(update_fields=["status", "updated_at"])


def _send(card: GiftCard) -> None:
    """The code to the person who receives it (WhatsApp or SMS), and a copy to the buyer."""
    pro = card.pro
    context = {
        "pro": pro.display_name,
        "amount": Money(card.amount_minor, card.currency).format("fr"),
        "code": card.code,
        "from": card.from_name,
        "message": card.message,
        "until": card.expires_on.isoformat(),
        "link": f"/{pro.slug}/rdv",
    }
    contact = card.recipient_contact
    if contact and "@" in contact:
        send_direct(
            "email",
            contact,
            gettext("A gift card from %(name)s") % {"name": card.from_name or pro.display_name},
            gettext("%(amount)s at %(pro)s. Code: %(code)s. Valid until %(until)s.") % context
            + ("\n\n" + card.message if card.message else ""),
        )
    elif contact:
        notify_contact(contact, "salon.gift_card_received", context)
    if card.buyer is not None:
        notify(card.buyer, "salon.gift_card_bought", context, link=f"/{pro.slug}")


def find(pro, code: str) -> GiftCard:
    card = (
        GiftCard.objects.select_for_update()
        .filter(pro=pro, code=(code or "").strip().upper().replace(" ", ""), status=G.ACTIVE)
        .first()
    )
    if card is None or card.expires_on < timezone.localdate():
        raise errors.GiftCardNotFound()
    return card


@transaction.atomic
def redeem(pro, code: str, amount_minor: int, *, actor=None, appointment=None, online=False):
    card = find(pro, code)
    if type(amount_minor) is not int or amount_minor <= 0:
        raise errors.InvalidPayment()
    if amount_minor > card.balance_minor:
        raise errors.NotEnoughBalance(
            details={"balance": Money(card.balance_minor, card.currency).format("fr")}
        )
    first = not card.uses.exists()
    GiftCardUse.objects.create(
        card=card, amount_minor=amount_minor, appointment=appointment, online=online, actor=actor
    )
    card.balance_minor -= amount_minor
    if card.balance_minor == 0:
        card.status = G.USED_UP
    card.save(update_fields=["balance_minor", "status", "updated_at"])
    if first:
        _release(card, "gift_card_used")
    record("salon.gift_card_used", card, actor=actor, metadata={"amount": amount_minor})
    return card


def _release(card: GiftCard, reason: str) -> None:
    if card.payment_id:
        payment = Payment.objects.get(pk=card.payment_id)
        if payment.status == PS.HELD:
            payment_services.release(payment, reason=reason)


def cover_deposit(appointment, code: str, actor) -> bool:
    """A booking deposit paid with a gift card of this salon (online)."""
    try:
        redeem(
            appointment.pro,
            code,
            appointment.deposit_minor,
            actor=actor,
            appointment=appointment,
            online=True,
        )
    except (errors.GiftCardNotFound, errors.NotEnoughBalance, errors.InvalidPayment):
        return False
    return True


def expire(today=None) -> int:
    """Past the date: the card cannot be used any more; its money goes to the pro."""
    today = today or timezone.localdate()
    count = 0
    for card in GiftCard.objects.filter(status=G.ACTIVE, expires_on__lt=today):
        with transaction.atomic():
            card.status = G.EXPIRED
            card.save(update_fields=["status", "updated_at"])
            _release(card, "gift_card_expired")
        count += 1
    return count
