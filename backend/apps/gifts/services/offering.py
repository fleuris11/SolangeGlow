"""Offering a gift: its price in euros, the payment, the sending on the chosen day, the
cancellation (refunded in euros while unused) and the end of its validity."""

from __future__ import annotations

import datetime
import secrets
from dataclasses import dataclass
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext, override

from apps.accounts.selectors import can_purchase
from apps.core.audit.services import record
from apps.core.media.models import MediaAsset
from apps.notifications.services import notify, notify_contact, send_direct
from apps.payments import services as payment_services
from apps.payments.models import Payment, Purpose

from .. import errors
from ..models import Gift, Occasion
from . import common

G = Gift.Status
PS = Payment.Status


@dataclass
class Quote:
    kind: str
    title: str
    value_minor: int  # FCFA received
    price_minor: int  # euros (cents) before the fee
    fee_minor: int
    rate: Decimal
    pro: object = None
    service: object = None
    variant: object = None
    quantity: int = 1
    delivery_mode: str = ""
    zone: object = None
    delivery_minor: int = 0
    selection_product: object = None
    option: str = ""

    @property
    def total_minor(self) -> int:
        return self.price_minor + self.fee_minor


def _service_quote(service_id) -> dict:
    from apps.pros.models import Service

    service = (
        Service.objects.select_related("pro__country", "pro__user")
        .filter(pk=service_id, is_active=True, archived_at__isnull=True)
        .first()
    )
    if (
        service is None
        or not service.pro.is_published
        or (service.pro.country.code if service.pro.country_id else "") not in common.countries()
        or service.price_kind != service.PriceKind.FIXED
        or not service.price_minor
        or service.currency != "XOF"
    ):
        raise errors.NothingToOffer()
    pro = service.pro
    return {
        "title": f"{service.name} — {pro.display_name}",
        "value_minor": service.price_minor,
        "pro": pro,
        "service": service,
    }


def _product_quote(variant_id, *, delivery_mode: str, zone_id) -> dict:
    from apps.shop import prices
    from apps.shop.models import DeliveryMode, DeliveryZone, Variant
    from apps.shop.selectors import on_sale, shop_of

    variant = (
        Variant.objects.select_related("product__pro__country", "product__pro__shop")
        .filter(pk=variant_id, is_active=True, product__in=on_sale())
        .first()
    )
    if variant is None or variant.stock < 1:
        raise errors.NothingToOffer()
    product, pro = variant.product, variant.product.pro
    shop = shop_of(pro)
    country = pro.country.code if pro.country_id else ""
    if shop is None or not shop.is_open or country not in common.countries():
        raise errors.NothingToOffer()
    offered = {
        DeliveryMode.PICKUP: shop.pickup,
        DeliveryMode.SELLER: shop.seller_delivery,
        DeliveryMode.PARTNER: shop.partner_delivery,
    }
    if not offered.get(delivery_mode):
        raise errors.NothingToOffer()
    zone = None
    if delivery_mode != DeliveryMode.PICKUP:
        zone = DeliveryZone.objects.filter(
            pk=zone_id, shop=shop, mode=delivery_mode, is_active=True
        ).first()
        if zone is None:
            raise errors.NothingToOffer()
    items = prices.unit_price(variant, prices.active_flash_sale(product))
    delivery = zone.fee_minor if zone else 0
    label = f" ({variant.label})" if variant.label else ""
    return {
        "title": f"{product.title}{label} — {pro.display_name}",
        "value_minor": items + delivery,
        "pro": pro,
        "variant": variant,
        "delivery_mode": delivery_mode,
        "zone": zone,
        "delivery_minor": delivery,
    }


def _selection_quote(product_id, *, option: str) -> dict:
    from apps.selection_france import selectors as selection
    from apps.selection_france.models import SelectionProduct

    product = selection.on_sale().filter(pk=product_id).first()
    option = (option or "").strip()
    if (
        product is None
        or product.availability != SelectionProduct.Availability.AVAILABLE
        or not product.price_xof
        or (product.options and option not in product.options)
        or (not product.options and option)
    ):
        raise errors.NothingToOffer()
    label = f" ({option})" if option else ""
    return {
        "title": f"{product.title}{label} — Sélection France",
        "value_minor": product.price_xof,
        "selection_product": product,
        "option": option,
    }


def quote(
    kind: str,
    *,
    service_id=None,
    variant_id=None,
    delivery_mode: str = "",
    zone_id=None,
    selection_product_id=None,
    option: str = "",
    amount_minor: int | None = None,
) -> Quote:
    """What the gift costs in euros (fee included) and what it is worth in FCFA."""
    eur_xof = common.rate()
    if kind == Gift.Kind.SERVICE:
        found = _service_quote(service_id)
    elif kind == Gift.Kind.PRODUCT:
        found = _product_quote(variant_id, delivery_mode=delivery_mode, zone_id=zone_id)
    elif kind == Gift.Kind.SELECTION:
        found = _selection_quote(selection_product_id, option=option)
    elif kind == Gift.Kind.CARD:
        low, high = common.card_limits()
        if type(amount_minor) is not int or not low <= amount_minor <= high:
            raise errors.InvalidAmount(
                details={"min": common.money(low, "EUR"), "max": common.money(high, "EUR")}
            )
        found = {
            "title": gettext("Glow gift card"),
            "value_minor": common.xof_for(amount_minor, eur_xof),
            "price_minor": amount_minor,
        }
    else:
        raise errors.WrongKind()
    price = found.pop("price_minor", None) or common.eur_for(found["value_minor"], eur_xof)
    fee = payment_services.buyer_fee(
        common.house_account(),
        purpose=Purpose.GIFT,
        items_minor=price,
        delivery_minor=0,
        currency="EUR",
    )
    return Quote(kind=kind, price_minor=price, fee_minor=fee, rate=eur_xof, **found)


def _send_at(value) -> datetime.datetime:
    now = timezone.now()
    if value is None or value <= now:
        return now
    days = int(common.setting("gifts.max_schedule_days", 365))
    if value > now + datetime.timedelta(days=days):
        raise errors.InvalidSendDate(details={"days": days})
    return value


@transaction.atomic
def offer(
    giver,
    the_quote: Quote,
    *,
    recipient_name: str,
    recipient_phone: str,
    recipient_email: str = "",
    language: str = "fr",
    occasion: str = Occasion.NONE,
    message: str = "",
    message_media_id=None,
    send_at=None,
    from_name: str = "",
) -> Gift:
    """The gift waiting for its payment in euros (the payment page is opened next)."""
    if not common.enabled(giver):
        raise errors.GiftsUnavailable()
    if not can_purchase(giver):
        raise errors.CannotOffer()
    pro = the_quote.pro
    if pro is not None and pro.user_id == giver.pk:
        raise errors.OfferYourself()
    name = " ".join((recipient_name or "").split())[:80]
    phone = common.recipient_phone(recipient_phone)
    if not name or not phone:
        raise errors.RecipientNeeded()
    media = None
    if message_media_id:
        media = MediaAsset.objects.filter(
            pk=message_media_id, owner=giver, purpose="gift_message"
        ).first()
    if occasion not in Occasion.values:
        occasion = Occasion.NONE
    days = int(common.setting("gifts.validity_days", 365))
    values = {
        "kind": the_quote.kind,
        "giver": giver,
        "from_name": (from_name or giver.first_name or "").strip()[:80] or "—",
        "recipient_name": name,
        "recipient_phone": phone,
        "recipient_email": (recipient_email or "").strip()[:254],
        "language": language if language in ("fr", "en", "sk") else "fr",
        "occasion": occasion,
        "message": (message or "").strip()[:500],
        "message_media": media,
        "send_at": _send_at(send_at),
        "token": secrets.token_urlsafe(32),
        "value_minor": the_quote.value_minor,
        "balance_minor": the_quote.value_minor,
        "price_minor": the_quote.price_minor,
        "rate": str(the_quote.rate),
        "pro": pro,
        "service": the_quote.service,
        "variant": the_quote.variant,
        "quantity": the_quote.quantity,
        "delivery_mode": the_quote.delivery_mode,
        "zone": the_quote.zone,
        "delivery_minor": the_quote.delivery_minor,
        "selection_product": the_quote.selection_product,
        "option": the_quote.option,
        "title": the_quote.title[:200],
        "expires_on": timezone.localdate() + datetime.timedelta(days=days),
    }
    for _attempt in range(5):
        try:
            with transaction.atomic():
                gift = Gift.objects.create(
                    reference=common.new_reference(), code=common.new_code(), **values
                )
            break
        except IntegrityError:  # the same code twice: very unlikely, try another one
            continue
    else:  # pragma: no cover - 32^10 codes
        raise RuntimeError("No free gift code")
    payment = payment_services.create_payment(
        giver,
        common.house_account(),
        purpose=Purpose.GIFT,
        items_minor=the_quote.price_minor,
        currency="EUR",
        description=gettext("Gift for %(name)s — %(what)s") % {"name": name, "what": gift.title},
        delivery_mode=Payment.Delivery.SERVICE,
        source_type=common.SOURCE,
        source_id=gift.pk,
    )
    gift.payment = payment
    gift.save(update_fields=["payment", "updated_at"])
    record("gifts.offered", gift, actor=giver)
    return gift


def start_payment(gift: Gift, giver) -> Payment:
    """The payment page of the provider (created once, reopened while it is valid)."""
    if gift.giver_id != giver.pk:
        raise errors.GiftNotFound()
    if gift.status != G.WAITING_PAYMENT or gift.payment_id is None:
        raise errors.AlreadyUsed()
    return payment_services.start_checkout(gift.payment, buyer=giver)


# --- The payment in euros ------------------------------------------------------------------------


def may_cancel_payment(payment: Payment, actor) -> bool:
    """Never from the payment page: the gift is cancelled from its own page."""
    return False


def on_payment_change(payment: Payment) -> None:
    with transaction.atomic():
        gift = Gift.objects.select_for_update().filter(payment=payment).first()
        if gift is None:
            return
        if payment.status == PS.HELD and gift.status == G.WAITING_PAYMENT:
            days = int(common.setting("gifts.cancel_days", 14))
            gift.status = G.SCHEDULED
            gift.cancel_until = timezone.now() + datetime.timedelta(days=days)
            gift.save(update_fields=["status", "cancel_until", "updated_at"])
            record("gifts.paid", gift)
            due = gift.send_at <= timezone.now()
            common.after_commit(lambda: _paid(gift.pk, send_now=due))
        elif payment.status == PS.CANCELLED and gift.status == G.WAITING_PAYMENT:
            gift.status = G.CANCELLED
            gift.save(update_fields=["status", "updated_at"])
        elif payment.status == PS.REFUNDED and gift.status != G.REFUNDED:
            gift.status = G.REFUNDED
            gift.save(update_fields=["status", "updated_at"])
            common.after_commit(
                lambda: notify(
                    gift.giver,
                    "gifts.refunded",
                    {"name": gift.recipient_name, "what": gift.title},
                    link=f"/cadeaux/{gift.pk}",
                )
            )


def _paid(gift_id, *, send_now: bool) -> None:
    gift = Gift.objects.select_related("giver").get(pk=gift_id)
    if send_now:
        send(gift)
        return
    notify(
        gift.giver,
        "gifts.scheduled",
        {"name": gift.recipient_name, "date": timezone.localtime(gift.send_at).date().isoformat()},
        link=f"/cadeaux/{gift.pk}",
    )


# --- Sending -------------------------------------------------------------------------------------


def _context(gift: Gift) -> dict:
    with override(gift.language):
        return {
            "name": gift.recipient_name,
            "from": gift.from_name,
            "what": gift.title,
            "occasion": gift.get_occasion_display() if gift.occasion != Occasion.NONE else "",
            "link": common.link(gift),
            "until": gift.expires_on.isoformat(),
        }


def _recipient_account(gift: Gift):
    if gift.recipient_user_id:
        return gift.recipient_user
    return get_user_model().objects.filter(phone=gift.recipient_phone, is_active=True).first()


def deliver(gift: Gift, event: str) -> None:
    """The message to the person who receives (WhatsApp, else SMS; her account; e-mail)."""
    context = _context(gift)
    notify_contact(gift.recipient_phone, event, context, language=gift.language)
    account = _recipient_account(gift)
    if account is not None and account.pk != gift.giver_id:
        notify(account, event, context, link=f"/cadeau/{gift.token}")
    if gift.recipient_email and event == "gifts.received":
        with override(gift.language):
            send_direct(
                "email",
                gift.recipient_email,
                gettext("%(from)s sends you a gift") % context,
                gettext("Open it here: %(link)s") % context
                + ("\n\n" + gift.message if gift.message else ""),
            )


def send(gift: Gift, *, actor=None) -> Gift:
    """Paid and the day has come: the person receives her link, the giver is told."""
    with transaction.atomic():
        gift = common.locked(gift)
        if gift.status != G.SCHEDULED:
            return gift
        gift.status = G.SENT
        gift.sent_at = timezone.now()
        gift.recipient_user = gift.recipient_user or _recipient_account(gift)
        if gift.recipient_user_id == gift.giver_id:
            gift.recipient_user = None
        gift.save(update_fields=["status", "sent_at", "recipient_user", "updated_at"])
        record("gifts.sent", gift, actor=actor)
    deliver(gift, "gifts.received")
    notify(
        gift.giver,
        "gifts.sent",
        {"name": gift.recipient_name, "what": gift.title},
        link=f"/cadeaux/{gift.pk}",
    )
    return gift


def resend(gift: Gift, *, actor) -> Gift:
    """The link again (lost message), at most a few times a day."""
    if actor is not None and not actor.is_staff and gift.giver_id != actor.pk:
        raise errors.GiftNotFound()
    if gift.status not in (G.SENT, G.OPENED, G.USED) or common.is_expired(gift):
        raise errors.WrongKind()
    deliver(gift, "gifts.received")
    record("gifts.resent", gift, actor=actor)
    return gift


def send_due(now=None) -> int:
    now = now or timezone.now()
    count = 0
    for gift in Gift.objects.filter(status=G.SCHEDULED, send_at__lte=now):
        send(gift)
        count += 1
    return count


# --- Cancel, expire, remind ----------------------------------------------------------------------


def cancel(gift: Gift, *, actor) -> Gift:
    """By the giver (unused, within the time) or the team (unused): refunded in euros."""
    with transaction.atomic():
        gift = common.locked(gift)
        staff = actor is not None and actor.is_staff
        if not staff and (actor is None or gift.giver_id != actor.pk):
            raise errors.GiftNotFound()
        if gift.status == G.WAITING_PAYMENT:
            payment_services.mark_not_paid(gift.payment, reason="gift_cancelled")
            gift.refresh_from_db()
            return gift
        in_time = gift.cancel_until is not None and timezone.now() <= gift.cancel_until
        if (
            gift.status not in (G.SCHEDULED, G.SENT, G.OPENED)
            or gift.uses.exists()
            or not (in_time or staff)
        ):
            raise errors.CannotCancel()
        payment = Payment.objects.get(pk=gift.payment_id)
        if payment.status != PS.HELD:
            raise errors.CannotCancel()
        payment_services.refund_full(payment, actor=actor, reason="gift_cancelled")
        record("gifts.cancelled", gift, actor=actor)
    gift.refresh_from_db()
    return gift


def release_euros(gift: Gift, reason: str) -> None:
    """The euros go to the platform once the gift is used (or over)."""
    if gift.payment_id is None:
        return
    payment = Payment.objects.get(pk=gift.payment_id)
    if payment.status == PS.HELD:
        payment_services.release(payment, reason=reason)


def expire(today=None) -> int:
    """Past its date, a gift cannot be used any more (what is left is lost)."""
    today = today or timezone.localdate()
    count = 0
    for gift in Gift.objects.filter(status__in=Gift.LIVE, expires_on__lt=today):
        with transaction.atomic():
            gift = common.locked(gift)
            gift.status = G.EXPIRED
            gift.save(update_fields=["status", "updated_at"])
            release_euros(gift, "gift_expired")
            record("gifts.expired", gift)
        count += 1
    return count


def remind(now=None) -> int:
    """Not opened or not used after a while: one reminder to the person."""
    now = now or timezone.now()
    days = int(common.setting("gifts.remind_after_days", 30))
    count = 0
    due = Gift.objects.filter(
        status__in=(G.SENT, G.OPENED),
        reminded_at__isnull=True,
        sent_at__lte=now - datetime.timedelta(days=days),
        uses__isnull=True,
    )
    for gift in due:
        Gift.objects.filter(pk=gift.pk).update(reminded_at=now)
        deliver(gift, "gifts.reminder")
        count += 1
    return count
