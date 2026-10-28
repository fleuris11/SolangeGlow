"""From the cart to the orders: one order per shop, paid together through one grouped
secure payment (module 5). The stock is taken when the orders are created and given back
if the payment never comes."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

import phonenumbers
from django.conf import settings
from django.db import transaction
from django.db.models import F

from apps.accounts.selectors import can_purchase
from apps.core.audit.services import record
from apps.payments import services as payment_services
from apps.payments.models import PaymentGroup, Purpose

from .. import errors
from ..models import CartItem, DeliveryMode, DeliveryZone, FlashSale, Order, OrderLine, Variant
from ..selectors import on_sale, shop_enabled, shop_of
from .cart import CartShop, cart_summary
from .promotions import discount_for, find_promo


@dataclass(frozen=True)
class ShopChoice:
    pro_id: uuid.UUID
    delivery_mode: str
    zone_id: uuid.UUID | None = None
    promo_code: str = ""
    note: str = ""


@dataclass
class Quote:
    cart: CartShop
    mode: str
    zone: DeliveryZone | None
    promo: object
    note: str
    discount_minor: int
    delivery_minor: int
    buyer_fee_minor: int

    @property
    def subtotal_minor(self) -> int:
        return self.cart.subtotal_minor

    @property
    def items_minor(self) -> int:
        return self.subtotal_minor - self.discount_minor

    @property
    def total_minor(self) -> int:
        return self.items_minor + self.delivery_minor + self.buyer_fee_minor


def normalize_phone(raw: str) -> str:
    """E.164, or empty when it is not a phone number."""
    try:
        number = phonenumbers.parse(raw or "", settings.PHONENUMBER_DEFAULT_REGION)
    except phonenumbers.NumberParseException:
        return ""
    if not phonenumbers.is_valid_number(number):
        return ""
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


def _check_lines(cart: CartShop) -> None:
    for line in cart.lines:
        if not line.available:
            raise errors.Unavailable(details={"title": line.title})
        if not line.enough:
            raise errors.OutOfStock(details={"title": line.title, "left": line.stock_left})


def _delivery(user, cart: CartShop, choice: ShopChoice) -> DeliveryZone | None:
    shop, pro = cart.shop, cart.pro
    offered = {
        DeliveryMode.PICKUP: shop.pickup,
        DeliveryMode.SELLER: shop.seller_delivery,
        DeliveryMode.PARTNER: shop.partner_delivery,
    }
    if not offered.get(choice.delivery_mode):
        raise errors.DeliveryNotOffered(details={"shop": pro.display_name})
    if choice.delivery_mode == DeliveryMode.PICKUP:
        return None
    # Delivery stays inside the country of the shop (pick-up is open to everybody).
    if user.country_id and pro.country_id and user.country_id != pro.country_id:
        raise errors.OutsideCountry(details={"shop": pro.display_name})
    zone = (
        DeliveryZone.objects.filter(
            pk=choice.zone_id, shop=shop, mode=choice.delivery_mode, is_active=True
        ).first()
        if choice.zone_id
        else None
    )
    if zone is None:
        raise errors.ZoneNeeded()
    return zone


def quote(user, choices: list[ShopChoice]) -> list[Quote]:
    """What each order will cost (also checks everything that can be checked before)."""
    if not can_purchase(user):
        raise errors.CannotBuy()
    carts = {cart.pro.pk: cart for cart in cart_summary(user)}
    if not choices or any(choice.pro_id not in carts for choice in choices):
        raise errors.EmptyCart()
    quotes = []
    for choice in choices:
        cart = carts[choice.pro_id]
        pro = cart.pro
        if pro.user_id == user.pk:
            raise errors.OwnShop()
        if not shop_enabled(pro.country):
            raise errors.ShopUnavailable()
        if not cart.shop.is_open:
            raise errors.ShopClosed(details={"shop": pro.display_name})
        _check_lines(cart)
        zone = _delivery(user, cart, choice)
        promo, discount = None, 0
        if choice.promo_code.strip():
            promo = find_promo(
                pro, choice.promo_code, buyer=user, subtotal_minor=cart.subtotal_minor
            )
            # Something is always left to pay: the secure payment needs an amount.
            discount = min(discount_for(promo, cart.subtotal_minor), cart.subtotal_minor - 1)
        delivery = zone.fee_minor if zone else 0
        fee = payment_services.buyer_fee(
            pro.user,
            purpose=Purpose.ORDER,
            items_minor=cart.subtotal_minor - discount,
            delivery_minor=delivery,
            currency=cart.currency,
            category=cart.category_key,
        )
        quotes.append(
            Quote(
                cart=cart,
                mode=choice.delivery_mode,
                zone=zone,
                promo=promo,
                note=(choice.note or "").strip()[:300],
                discount_minor=discount,
                delivery_minor=delivery,
                buyer_fee_minor=fee,
            )
        )
    if len({q.cart.currency for q in quotes}) > 1:
        raise errors.MixedCurrencies()
    return quotes


def _take_stock(quote: Quote) -> None:
    for line in quote.cart.lines:
        for variant_id, quantity in line.stock_needs():
            taken = Variant.objects.filter(pk=variant_id, stock__gte=quantity).update(
                stock=F("stock") - quantity
            )
            if not taken:
                left = Variant.objects.filter(pk=variant_id).values_list("stock", flat=True)
                raise errors.OutOfStock(details={"title": line.title, "left": left.first() or 0})
        sale = line.flash_sale
        if sale is not None:
            sold = FlashSale.objects.filter(pk=sale.pk)
            if sale.quantity_limit is not None:
                sold = sold.filter(sold_count__lte=sale.quantity_limit - line.quantity)
            if not sold.update(sold_count=F("sold_count") + line.quantity):
                left = max((sale.quantity_limit or 0) - sale.sold_count, 0)
                raise errors.OutOfStock(details={"title": line.title, "left": left})


def _description(quote: Quote) -> str:
    items = ", ".join(f"{line.title} x{line.quantity}" for line in quote.cart.lines)
    return f"{quote.cart.pro.display_name} — {items}"[:200]


@transaction.atomic
def place_orders(
    user,
    choices: list[ShopChoice],
    *,
    address: str = "",
    landmarks: str = "",
    phone: str = "",
) -> tuple[PaymentGroup, list[Order]]:
    """Creates the orders (one per shop) and their grouped payment, waiting to be paid."""
    quotes = quote(user, choices)
    delivering = any(q.mode != DeliveryMode.PICKUP for q in quotes)
    address = re.sub(r"\s+", " ", address or "").strip()[:255]
    phone = normalize_phone(phone) if phone else ""
    if delivering and (not address or not phone):
        raise errors.AddressNeeded()
    payments, orders = [], []
    for q in quotes:
        cart, pro = q.cart, q.cart.pro
        _take_stock(q)
        order_id = uuid.uuid4()
        payment = payment_services.create_payment(
            user,
            pro.user,
            purpose=Purpose.ORDER,
            items_minor=q.items_minor,
            currency=cart.currency,
            description=_description(q),
            delivery_minor=q.delivery_minor,
            delivery_mode=q.mode,
            category=cart.category_key,
            source_type="order",
            source_id=order_id,
            prep_days=cart.prep_days,
        )
        delivered = q.mode != DeliveryMode.PICKUP
        order = Order.objects.create(
            id=order_id,
            reference=payment.reference,
            buyer=user,
            pro=pro,
            payment=payment,
            currency=cart.currency,
            subtotal_minor=q.subtotal_minor,
            discount_minor=q.discount_minor,
            items_minor=q.items_minor,
            delivery_minor=q.delivery_minor,
            promo_code=q.promo,
            promo_label=q.promo.code if q.promo else "",
            delivery_mode=q.mode,
            zone=q.zone,
            zone_name=q.zone.name if q.zone else "",
            partner_name=cart.shop.partner_name if q.mode == DeliveryMode.PARTNER else "",
            address=address if delivered else "",
            landmarks=(landmarks or "").strip()[:500] if delivered else "",
            contact_phone=phone if delivered else "",
            note=q.note,
            prep_days=cart.prep_days,
            sale_live_id=next(
                (line.item.sale_live_id for line in cart.lines if line.item.sale_live_id), None
            ),
        )
        OrderLine.objects.bulk_create(
            OrderLine(
                order=order,
                product=line.product,
                variant=line.item.variant,
                bundle=line.bundle,
                flash_sale=line.flash_sale,
                title=line.title[:120],
                variant_label=line.variant_label[:140],
                photo=line.photo,
                category_key=line.category_key,
                unit_price_minor=line.unit_price_minor,
                quantity=line.quantity,
                total_minor=line.total_minor,
                components=[
                    {"variant": str(variant_id), "quantity": quantity}
                    for variant_id, quantity in line.stock_needs()
                ]
                if line.bundle is not None
                else [],
            )
            for line in cart.lines
        )
        CartItem.objects.filter(pk__in=[line.item.pk for line in cart.lines]).delete()
        record("shop.order_created", order, actor=user)
        payments.append(payment)
        orders.append(order)
    group = payment_services.create_group(user, payments)
    return group, orders


@transaction.atomic
def place_gift_order(
    buyer,
    variant_id,
    *,
    quantity: int,
    items_minor: int,
    delivery_mode: str,
    zone_id=None,
    delivery_minor: int = 0,
    address: str = "",
    landmarks: str = "",
    phone: str = "",
    note: str = "",
) -> Order:
    """An offered product (gifts, ADR-014): one order at the price paid by the person who
    offers it (she is the client, abroad), delivered to the person who receives it."""
    variant = (
        Variant.objects.select_related("product__pro", "product__category")
        .filter(pk=variant_id, is_active=True)
        .first()
    )
    if variant is None:
        raise errors.Unavailable(details={"title": ""})
    product = variant.product
    pro = product.pro
    shop = shop_of(pro)
    title = product.title
    sellable = on_sale().filter(pk=product.pk).exists()
    if not sellable or not shop_enabled(pro.country) or not shop.is_open:
        raise errors.Unavailable(details={"title": title})
    zone = None
    if delivery_mode != DeliveryMode.PICKUP:
        zone = DeliveryZone.objects.filter(
            pk=zone_id, shop=shop, mode=delivery_mode, is_active=True
        ).first()
        if zone is None:
            raise errors.ZoneNeeded()
    address = re.sub(r"\s+", " ", address or "").strip()[:255]
    phone = normalize_phone(phone) if phone else ""
    delivered = delivery_mode != DeliveryMode.PICKUP
    if delivered and (not address or not phone):
        raise errors.AddressNeeded()
    if not Variant.objects.filter(pk=variant.pk, stock__gte=quantity).update(
        stock=F("stock") - quantity
    ):
        raise errors.OutOfStock(details={"title": title, "left": variant.stock})
    order_id = uuid.uuid4()
    category = product.category.key if product.category_id else ""
    payment = payment_services.create_payment(
        buyer,
        pro.user,
        purpose=Purpose.ORDER,
        items_minor=items_minor,
        currency=product.currency,
        description=f"{pro.display_name} — {title} x{quantity}"[:200],
        delivery_minor=delivery_minor,
        delivery_mode=delivery_mode,
        category=category,
        source_type="order",
        source_id=order_id,
        prep_days=product.prep_days,
        with_buyer_fee=False,
    )
    order = Order.objects.create(
        id=order_id,
        reference=payment.reference,
        buyer=buyer,
        pro=pro,
        payment=payment,
        currency=product.currency,
        subtotal_minor=items_minor,
        items_minor=items_minor,
        delivery_minor=delivery_minor,
        delivery_mode=delivery_mode,
        zone=zone,
        zone_name=zone.name if zone else "",
        partner_name=shop.partner_name if delivery_mode == DeliveryMode.PARTNER else "",
        address=address if delivered else "",
        landmarks=(landmarks or "").strip()[:500] if delivered else "",
        contact_phone=phone if delivered else "",
        note=(note or "").strip()[:300],
        prep_days=product.prep_days,
    )
    first = product.photos.first()
    OrderLine.objects.create(
        order=order,
        product=product,
        variant=variant,
        title=title[:120],
        variant_label=variant.label[:140],
        photo=first.media if first else None,
        category_key=category,
        unit_price_minor=items_minor // quantity,
        quantity=quantity,
        total_minor=items_minor,
    )
    record("shop.order_created", order, actor=buyer, metadata={"gift": True})
    return order
