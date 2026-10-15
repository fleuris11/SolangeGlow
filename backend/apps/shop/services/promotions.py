"""Promotions of a pro: promo codes (she pays the discount), flash sales with a countdown,
bundles (several products for one price)."""

from __future__ import annotations

import datetime
import uuid

from django.db import transaction
from django.utils import timezone

from apps.core.money import Money
from apps.core.selectors import get_setting

from .. import errors, prices
from ..models import Bundle, BundleItem, FlashSale, Order, Product, PromoCode, Variant
from .catalog import _media, pro_of

OS = Order.Status


def _setting(key: str, pro, default):
    return get_setting(key, country=pro.country, default=default)


def _optional_count(value):
    if value is None:
        return None
    if type(value) is not int or value < 1:
        raise errors.InvalidPromo()
    return value


# --- Promo codes ---------------------------------------------------------------------------------


def save_promo(
    user,
    *,
    promo_id=None,
    code: str,
    percent_off: int | None = None,
    amount_off_minor: int | None = None,
    min_order_minor: int = 0,
    starts_at=None,
    ends_at=None,
    max_uses: int | None = None,
    max_per_client: int = 1,
    is_active: bool = True,
) -> PromoCode:
    pro = pro_of(user)
    code = "".join((code or "").split()).upper()[:20]
    if not code or (percent_off is None) == (amount_off_minor is None):
        raise errors.InvalidPromo()
    if percent_off is not None:
        maximum = int(_setting("shop.promo_max_percent", pro, 70))
        if type(percent_off) is not int or percent_off < 1:
            raise errors.InvalidPromo()
        if percent_off > maximum:
            raise errors.PromoTooHigh(details={"max": maximum})
    elif type(amount_off_minor) is not int or amount_off_minor < 1:
        raise errors.InvalidPromo()
    if type(min_order_minor) is not int or min_order_minor < 0:
        raise errors.InvalidPromo()
    if starts_at and ends_at and ends_at <= starts_at:
        raise errors.InvalidPromo()
    max_uses = _optional_count(max_uses)
    max_per_client = _optional_count(max_per_client) or 1
    promo = (
        PromoCode.objects.filter(pk=promo_id, pro=pro).first() if promo_id else PromoCode(pro=pro)
    )
    if promo is None:
        raise errors.PromoNotFound()
    if PromoCode.objects.filter(pro=pro, code=code).exclude(pk=promo.pk).exists():
        raise errors.CodeTaken()
    promo.code = code
    promo.percent_off = percent_off
    promo.amount_off_minor = amount_off_minor
    promo.currency = pro.currency or "XOF"
    promo.min_order_minor = min_order_minor
    promo.starts_at, promo.ends_at = starts_at, ends_at
    promo.max_uses, promo.max_per_client = max_uses, max_per_client
    promo.is_active = bool(is_active)
    promo.save()
    return promo


def delete_promo(user, promo_id) -> None:
    deleted, _ = PromoCode.objects.filter(pk=promo_id, pro=pro_of(user)).delete()
    if not deleted:
        raise errors.PromoNotFound()


def uses_of(promo: PromoCode, buyer=None) -> int:
    orders = Order.objects.filter(promo_code=promo).exclude(status=OS.CANCELLED)
    if buyer is not None:
        orders = orders.filter(buyer=buyer)
    return orders.count()


def discount_for(promo: PromoCode, subtotal_minor: int) -> int:
    if promo.percent_off is not None:
        return subtotal_minor - prices.percent_off(subtotal_minor, promo.percent_off)
    return min(promo.amount_off_minor, subtotal_minor)


def find_promo(pro, code: str, *, buyer, subtotal_minor: int, now=None) -> PromoCode:
    """The code of this shop if the client can use it on this order now."""
    now = now or timezone.now()
    code = "".join((code or "").split()).upper()
    promo = PromoCode.objects.filter(pro=pro, code=code, is_active=True).first()
    if promo is None:
        raise errors.PromoNotFound()
    if (promo.starts_at and promo.starts_at > now) or (promo.ends_at and promo.ends_at <= now):
        raise errors.PromoOver()
    if subtotal_minor < promo.min_order_minor:
        language = getattr(buyer, "preferred_language", "") or "fr"
        minimum = Money(promo.min_order_minor, promo.currency).format(language)
        raise errors.PromoMinimum(details={"minimum": minimum})
    if promo.max_uses is not None and uses_of(promo) >= promo.max_uses:
        raise errors.PromoUsedUp()
    if uses_of(promo, buyer) >= promo.max_per_client:
        raise errors.PromoUsedUp()
    return promo


# --- Flash sales ---------------------------------------------------------------------------------


@transaction.atomic
def create_flash_sale(
    user,
    *,
    product_id,
    percent_off: int,
    starts_at: datetime.datetime,
    ends_at: datetime.datetime,
    quantity_limit: int | None = None,
) -> FlashSale:
    pro = pro_of(user)
    product = (
        Product.objects.select_for_update()
        .filter(pk=product_id, pro=pro)
        .exclude(status=Product.Status.ARCHIVED)
        .first()
    )
    if product is None:
        raise errors.ProductNotFound()
    days = int(_setting("shop.flash_sale_max_days", pro, 7))
    now = timezone.now()
    if (
        type(percent_off) is not int
        or not 1 <= percent_off <= 90
        or ends_at <= starts_at
        or ends_at <= now
        or ends_at - starts_at > datetime.timedelta(days=days)
        or FlashSale.objects.filter(
            product=product, starts_at__lt=ends_at, ends_at__gt=starts_at
        ).exists()
    ):
        raise errors.InvalidFlashSale(details={"max": days})
    if quantity_limit is not None and (type(quantity_limit) is not int or quantity_limit < 1):
        raise errors.InvalidFlashSale(details={"max": days})
    sale = FlashSale.objects.create(
        product=product,
        percent_off=percent_off,
        starts_at=starts_at,
        ends_at=ends_at,
        quantity_limit=quantity_limit,
    )
    if starts_at <= now:
        from . import alerts

        sale.announced_at = now
        sale.save(update_fields=["announced_at", "updated_at"])
        transaction.on_commit(lambda: alerts.after_change(product.pk, [], True))
    return sale


def end_flash_sale(user, sale_id) -> None:
    """Not started yet: deleted. Running: it ends now."""
    sale = FlashSale.objects.filter(pk=sale_id, product__pro=pro_of(user)).first()
    if sale is None:
        raise errors.ProductNotFound()
    now = timezone.now()
    if sale.starts_at > now:
        sale.delete()
    elif sale.ends_at > now:
        sale.ends_at = now
        sale.save(update_fields=["ends_at", "updated_at"])


# --- Bundles -------------------------------------------------------------------------------------


@transaction.atomic
def save_bundle(
    user,
    *,
    bundle_id=None,
    title: str,
    price_minor: int,
    items: list[dict],
    description: str = "",
    photo_id=None,
    is_active: bool = True,
) -> Bundle:
    pro = pro_of(user)
    title = (title or "").strip()[:120]
    wanted = {}
    for item in items or []:
        quantity = item.get("quantity", 1)
        if type(quantity) is not int or quantity < 1:
            raise errors.InvalidBundle()
        wanted[str(item.get("variant_id"))] = quantity
    variants = {
        str(v.pk): v
        for v in Variant.objects.filter(
            pk__in=[key for key in wanted if _is_uuid(key)],
            product__pro=pro,
            is_active=True,
        ).exclude(product__status=Product.Status.ARCHIVED)
    }
    if (
        not title
        or type(price_minor) is not int
        or price_minor < 1
        or len(variants) != len(wanted)
        or sum(wanted.values()) < 2
    ):
        raise errors.InvalidBundle()
    bundle = Bundle.objects.filter(pk=bundle_id, pro=pro).first() if bundle_id else Bundle(pro=pro)
    if bundle is None:
        raise errors.InvalidBundle()
    bundle.title = title
    bundle.description = (description or "").strip()[:1000]
    bundle.photo = _media(user, photo_id, "product_photo")
    bundle.price_minor = price_minor
    bundle.currency = pro.currency or "XOF"
    bundle.is_active = bool(is_active)
    bundle.save()
    BundleItem.objects.filter(bundle=bundle).delete()
    BundleItem.objects.bulk_create(
        BundleItem(bundle=bundle, variant=variants[key], quantity=quantity)
        for key, quantity in wanted.items()
    )
    return bundle


def delete_bundle(user, bundle_id) -> None:
    deleted, _ = Bundle.objects.filter(pk=bundle_id, pro=pro_of(user)).delete()
    if not deleted:
        raise errors.InvalidBundle()


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True
