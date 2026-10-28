"""Reads of the gifts: the page of the person who receives, the follow-up of the giver,
gift ideas, and the amount the platform owes in FCFA."""

from __future__ import annotations

from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.core.media.services import asset_payload
from apps.payments import services as payment_services

from .models import Gift, GiftUse, Occasion
from .services import common
from .services.proof import candidates

G = Gift.Status


def _amount(minor: int, currency: str) -> dict:
    return {"amount_minor": minor, "currency": currency}


def _photo_of(media) -> dict | None:
    return asset_payload(media) if media is not None else None


def _pro(gift: Gift) -> dict | None:
    pro = gift.pro
    if pro is None:
        return None
    return {
        "slug": pro.slug,
        "name": pro.display_name,
        "photo": _photo_of(pro.photo),
        "city": pro.city,
    }


def _thing(gift: Gift) -> dict:
    """The offered service or product: its picture, and whether it can still be had."""
    from apps.pros.models import Service

    if gift.kind == Gift.Kind.SERVICE and gift.service_id:
        service = gift.service
        available = (
            service.is_active
            and service.archived_at is None
            and gift.pro.is_published
            and Service.objects.filter(pk=service.pk).exists()
        )
        return {
            "name": service.name,
            "photo": None,
            "duration_minutes": service.duration_minutes,
            "available": available,
        }
    if gift.kind == Gift.Kind.PRODUCT and gift.variant_id:
        from apps.shop.selectors import on_sale

        product = gift.variant.product
        first = product.photos.select_related("media").first()
        available = (
            gift.variant.is_active
            and gift.variant.stock >= gift.quantity
            and on_sale().filter(pk=product.pk).exists()
        )
        return {
            "name": product.title,
            "photo": _photo_of(first.media if first else None),
            "variant": gift.variant.label,
            "delivery_mode": gift.delivery_mode,
            "zone": gift.zone.name if gift.zone_id else "",
            "available": available,
        }
    if gift.kind == Gift.Kind.SELECTION and gift.selection_product_id:
        from apps.selection_france import selectors as selection

        product = gift.selection_product
        first = product.photos.select_related("media").first()
        return {
            "name": product.title,
            "photo": _photo_of(first.media if first else None),
            "variant": gift.option,
            "available": selection.on_sale().filter(pk=product.pk).exists(),
        }
    return {"name": gift.title, "photo": None, "available": True}


def _uses(gift: Gift) -> list[dict]:
    """What the gift paid: the appointment, the order, purchases with the card."""
    from apps.booking.models import Appointment
    from apps.booking.services.common import manage_link
    from apps.selection_france.models import SelectionOrder
    from apps.shop.models import Order

    rows = []
    for use in gift.uses.select_related("payment").order_by("created_at"):
        payment = use.payment
        row = {
            "id": str(use.pk),
            "label": use.label,
            "kind": use.source_type,
            "amount": _amount(use.amount_minor, gift.currency),
            "refunded": _amount(use.refunded_minor, gift.currency),
            "payment_status": payment.status,
            "created_at": use.created_at.isoformat(),
            "starts_at": None,
            "status": "",
            "link": "",
            "receipt_code": None,
            "pickup_point": "",
        }
        if use.source_type == "booking":
            appointment = Appointment.objects.filter(pk=use.source_id).first()
            if appointment is not None:
                row["starts_at"] = appointment.starts_at.isoformat()
                row["status"] = appointment.status
                row["link"] = (
                    f"/appointments/{appointment.pk}"
                    if appointment.client_id
                    else manage_link(appointment)
                )
        elif use.source_type == "order":
            order = Order.objects.filter(pk=use.source_id).first()
            if order is not None:
                row["status"] = order.status
                row["receipt_code"] = payment_services.receipt_code_of(payment)
        elif use.source_type == "selection":
            order = SelectionOrder.objects.select_related("pickup_point").filter(pk=use.source_id)
            order = order.first()
            if order is not None:
                row["status"] = order.status
                row["receipt_code"] = payment_services.receipt_code_of(payment)
                point = order.pickup_point
                row["pickup_point"] = f"{point.name}, {point.city}" if point else ""
        rows.append(row)
    return rows


def _pickup_points(gift: Gift) -> list[dict]:
    if gift.kind != Gift.Kind.SELECTION:
        return []
    from apps.selection_france.models import PickupPoint

    return [
        {"id": str(p.pk), "name": p.name, "city": p.city, "address": p.address, "hours": p.hours}
        for p in PickupPoint.objects.filter(is_active=True).order_by("position", "name")
    ]


def _time_zone(gift: Gift) -> str:
    if gift.pro is None:
        return "Africa/Porto-Novo"
    from apps.pros.hours import zone_of

    return str(zone_of(gift.pro))


def reception(gift: Gift, viewer=None) -> dict:
    """The page of the gift, for the person who receives it (or a preview for the giver)."""
    from .services.using import is_giver

    locked = gift.status == G.SCHEDULED
    giver = is_giver(gift, viewer)
    base = {
        "status": gift.status,
        "kind": gift.kind,
        "locked": locked,
        "opens_at": gift.send_at.isoformat(),
        "is_giver": giver,
        "from_name": gift.from_name,
        "recipient_name": gift.recipient_name,
        "occasion": gift.occasion,
    }
    if locked:
        return base
    usable = common.usable(gift)
    show_code = gift.kind == Gift.Kind.CARD and usable
    return {
        **base,
        "message": gift.message,
        "message_media": _photo_of(gift.message_media),
        "title": gift.title,
        "value": _amount(gift.value_minor, gift.currency),
        "balance": _amount(gift.balance_minor, gift.currency),
        "expires_on": gift.expires_on.isoformat(),
        "expired": common.is_expired(gift) or gift.status == G.EXPIRED,
        "cancelled": gift.status == G.REFUNDED,
        "usable": usable,
        "unused": gift.balance_minor == gift.value_minor,
        "code": gift.code if show_code else None,
        "claimed": bool(viewer and gift.recipient_user_id == getattr(viewer, "pk", None)),
        "pro": _pro(gift),
        "service_id": str(gift.service_id) if gift.service_id else None,
        "thing": _thing(gift),
        "uses": _uses(gift),
        "pickup_points": _pickup_points(gift),
        "recipient_phone": gift.recipient_phone if not giver else "",
        "time_zone": _time_zone(gift),
        "photos": []
        if giver
        else [
            {"id": str(media.pk), "source": source, "media": asset_payload(media)}
            for media, source in candidates(gift)
        ],
        "proof_status": gift.proof_status,
        "proof_sent_id": str(gift.proof_media_id) if gift.proof_media_id else None,
    }


def _steps(gift: Gift) -> list[dict]:
    """The follow-up of the giver: paid, sent, opened, used, photo."""
    used = gift.uses.order_by("created_at").first()
    return [
        {
            "key": "paid",
            "at": gift.payment.paid_at.isoformat()
            if gift.payment_id and gift.payment.paid_at
            else None,
        },
        {"key": "sent", "at": gift.sent_at.isoformat() if gift.sent_at else None},
        {"key": "opened", "at": gift.opened_at.isoformat() if gift.opened_at else None},
        {"key": "used", "at": used.created_at.isoformat() if used else None},
        {"key": "photo", "at": gift.proof_sent_at.isoformat() if gift.proof_sent_at else None},
    ]


def summary(gift: Gift) -> dict:
    payment = gift.payment
    return {
        "id": str(gift.pk),
        "reference": gift.reference,
        "kind": gift.kind,
        "status": gift.status,
        "title": gift.title,
        "recipient_name": gift.recipient_name,
        "occasion": gift.occasion,
        "send_at": gift.send_at.isoformat(),
        "value": _amount(gift.value_minor, gift.currency),
        "balance": _amount(gift.balance_minor, gift.currency),
        "paid": _amount(payment.total_minor, payment.currency) if payment else None,
        "created_at": gift.created_at.isoformat(),
        "proof_status": gift.proof_status,
        "pro": _pro(gift),
        "photo": _thing(gift).get("photo"),
    }


def for_giver(gift: Gift) -> dict:
    payment = gift.payment
    can_cancel = (
        gift.status in (G.SCHEDULED, G.SENT, G.OPENED)
        and not gift.uses.exists()
        and gift.cancel_until is not None
        and timezone.now() <= gift.cancel_until
    )
    return {
        **summary(gift),
        "from_name": gift.from_name,
        "recipient_phone": gift.recipient_phone,
        "message": gift.message,
        "message_media": _photo_of(gift.message_media),
        "link": common.link(gift),
        "code": gift.code if gift.kind == Gift.Kind.CARD else None,
        "price": _amount(gift.price_minor, gift.price_currency),
        "fee": _amount(payment.buyer_fee_minor, payment.currency) if payment else None,
        "payment_id": str(payment.pk) if payment else None,
        "payment_status": payment.status if payment else "",
        "checkout_url": payment.checkout_url
        if payment and payment.status == payment.Status.PENDING_PAYMENT
        else "",
        "expires_on": gift.expires_on.isoformat(),
        "cancel_until": gift.cancel_until.isoformat() if gift.cancel_until else None,
        "can_cancel": can_cancel,
        "can_resend": common.usable(gift),
        "steps": _steps(gift),
        "uses": [
            {k: v for k, v in row.items() if k not in ("receipt_code", "link")}
            for row in _uses(gift)
        ],
        "proof": _photo_of(gift.proof_media) if gift.proof_status == Gift.Proof.SENT else None,
    }


def sent_by(user):
    return (
        Gift.objects.filter(giver=user)
        .exclude(status=G.CANCELLED)
        .select_related("payment", "pro", "service", "variant__product", "selection_product")
        .order_by("-created_at")
    )


def received_by(user):
    """Gifts kept in her account (Glow gift cards first), or sent to her number."""
    phone = str(user.phone or "")
    who = Q(recipient_user=user) | (Q(recipient_phone=phone) if phone else Q(pk__in=[]))
    return (
        Gift.objects.filter(who, status__in=Gift.LIVE)
        .exclude(giver=user)
        .select_related("payment", "pro", "service", "variant__product", "selection_product")
        .order_by("expires_on")
    )


def received_payload(gift: Gift) -> dict:
    return {
        **summary(gift),
        "from_name": gift.from_name,
        "token": gift.token,
        "code": gift.code if gift.kind == Gift.Kind.CARD else None,
        "expires_on": gift.expires_on.isoformat(),
    }


def occasions() -> list[str]:
    return list(Occasion.values)


def ideas(limit: int = 12) -> dict:
    """Things people like to offer: products of shops in Benin, France Selection."""
    from apps.selection_france import selectors as selection
    from apps.shop import prices
    from apps.shop.selectors import on_sale

    countries = common.countries()
    rows = []
    products = (
        on_sale()
        .filter(pro__country__code__in=countries, variants__stock__gt=0)
        .select_related("pro")
        .prefetch_related("variants", "photos__media", "flash_sales")
        .distinct()
        .order_by("-sold_count", "-published_at")[:limit]
    )
    for product in products:
        first = product.photos.all()[0] if product.photos.all() else None
        price, _before = prices.lowest_price(product)
        rows.append(
            {
                "kind": Gift.Kind.PRODUCT,
                "id": str(product.pk),
                "slug": product.slug,
                "shop": product.pro.slug,
                "shop_name": product.pro.display_name,
                "title": product.title,
                "photo": _photo_of(first.media if first else None),
                "price": _amount(price, product.currency),
            }
        )
    selection_rows = []
    for product in (
        selection.on_sale()
        .filter(availability="available", price_xof__gt=0)
        .order_by("-sold_count")[: limit // 2]
    ):
        first = product.photos.all()[0] if product.photos.all() else None
        selection_rows.append(
            {
                "kind": Gift.Kind.SELECTION,
                "id": str(product.pk),
                "slug": product.slug,
                "shop": "",
                "shop_name": "Sélection France",
                "title": product.title,
                "photo": _photo_of(first.media if first else None),
                "price": _amount(product.price_xof, "XOF"),
            }
        )
    return {"products": rows, "selection": selection_rows}


def owed(since=None) -> dict:
    """FCFA paid by gifts (minus what came back), to cover from the euros received."""
    rows = GiftUse.objects.all()
    if since is not None:
        rows = rows.filter(created_at__gte=since)
    totals = rows.aggregate(
        spent=Sum("amount_minor"), back=Sum("refunded_minor"), count=Count("pk")
    )
    spent = (totals["spent"] or 0) - (totals["back"] or 0)
    return {"xof_minor": spent, "count": totals["count"] or 0}


def _limits() -> dict:
    low, high = common.card_limits()
    return {"card_min": _amount(low, "EUR"), "card_max": _amount(high, "EUR")}


def ideas_payload() -> dict:
    return {**ideas(), **_limits()}


def quote_payload(found) -> dict:
    """What the giver sees before paying: the price in euros, the value in FCFA."""
    photo = None
    if found.variant is not None:
        first = found.variant.product.photos.select_related("media").first()
        photo = _photo_of(first.media if first else None)
    elif found.selection_product is not None:
        first = found.selection_product.photos.select_related("media").first()
        photo = _photo_of(first.media if first else None)
    elif found.pro is not None:
        photo = _photo_of(found.pro.photo)
    pro = found.pro
    return {
        "kind": found.kind,
        "title": found.title,
        "value": _amount(found.value_minor, "XOF"),
        "price": _amount(found.price_minor, "EUR"),
        "fee": _amount(found.fee_minor, "EUR"),
        "total": _amount(found.total_minor, "EUR"),
        "rate": str(found.rate),
        "validity_days": int(common.setting("gifts.validity_days", 365)),
        "cancel_days": int(common.setting("gifts.cancel_days", 14)),
        "message_max_seconds": int(common.setting("gifts.message_max_seconds", 60)),
        "photo": photo,
        "pro": {
            "slug": pro.slug,
            "name": pro.display_name,
            "photo": _photo_of(pro.photo),
            "city": pro.city,
        }
        if pro is not None
        else None,
        **_limits(),
    }


def product_options(variant_id) -> dict:
    """How an offered product can reach the person: pick-up and the delivery zones."""
    from apps.shop.models import DeliveryMode, DeliveryZone, Variant

    variant = Variant.objects.select_related("product__pro__shop").filter(pk=variant_id).first()
    from apps.shop.selectors import shop_of

    shop = shop_of(variant.product.pro) if variant is not None else None
    if shop is None:
        return {"pickup": False, "zones": []}
    modes = [
        m
        for m, on in (
            (DeliveryMode.SELLER, shop.seller_delivery),
            (DeliveryMode.PARTNER, shop.partner_delivery),
        )
        if on
    ]
    zones = DeliveryZone.objects.filter(shop=shop, mode__in=modes, is_active=True).order_by(
        "fee_minor", "name"
    )
    return {
        "pickup": bool(shop.pickup),
        "zones": [
            {
                "id": str(z.pk),
                "mode": z.mode,
                "name": z.name,
                "fee": _amount(z.fee_minor, variant.product.currency),
            }
            for z in zones
        ],
    }
