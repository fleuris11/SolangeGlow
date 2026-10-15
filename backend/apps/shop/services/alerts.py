"""Wishlist, « tell me when it is back » and price drops."""

from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from apps.accounts.selectors import can_purchase
from apps.core.money import Money
from apps.core.selectors import get_setting
from apps.notifications.services import notify

from .. import errors, prices
from ..models import FlashSale, Product, StockAlert, Variant, WishlistItem
from ..selectors import on_sale


def product_link(product: Product) -> str:
    return f"/{product.pro.slug}/shop/{product.slug}"


def _price(product: Product) -> int:
    product._flash_sales = None  # a fresh look at the sales
    return prices.lowest_price(product)[0]


def add_to_wishlist(user, product_id) -> WishlistItem:
    product = on_sale().select_related("pro").filter(pk=product_id).first()
    if product is None:
        raise errors.ProductNotFound()
    item, _ = WishlistItem.objects.get_or_create(
        user=user, product=product, defaults={"price_seen_minor": _price(product)}
    )
    return item


def remove_from_wishlist(user, product_id) -> None:
    WishlistItem.objects.filter(user=user, product_id=product_id).delete()


def watch_stock(user, variant_id) -> StockAlert:
    if not can_purchase(user):
        raise errors.CannotBuy()
    variant = Variant.objects.filter(pk=variant_id, is_active=True, product__in=on_sale()).first()
    if variant is None:
        raise errors.ProductNotFound()
    alert, _ = StockAlert.objects.get_or_create(user=user, variant=variant)
    return alert


def unwatch_stock(user, variant_id) -> None:
    StockAlert.objects.filter(user=user, variant_id=variant_id).delete()


def notify_back_in_stock(variant_ids) -> int:
    """Everybody waiting for one of these variants, now in stock, is told once."""
    sent = 0
    for variant in Variant.objects.filter(
        pk__in=variant_ids, stock__gt=0, is_active=True
    ).select_related("product__pro"):
        product = variant.product
        if product.status != Product.Status.PUBLISHED:
            continue
        for alert in StockAlert.objects.filter(variant=variant).select_related("user"):
            notify(
                alert.user,
                "shop.back_in_stock",
                {"product": product.title, "choice": variant.label},
                link=product_link(product),
            )
            alert.delete()
            sent += 1
    return sent


def check_price_drop(product_id, now=None) -> int:
    """Wishlists of this product: a drop of at least the setting, not too often."""
    now = now or timezone.now()
    product = Product.objects.select_related("pro").filter(pk=product_id).first()
    if product is None or product.status != Product.Status.PUBLISHED:
        return 0
    price = _price(product)
    threshold = int(
        get_setting("shop.price_drop_min_percent", country=product.pro.country, default=10)
    )
    days = int(
        get_setting("shop.price_alert_cooldown_days", country=product.pro.country, default=7)
    )
    sent = 0
    for item in WishlistItem.objects.filter(product=product).select_related("user"):
        seen = item.price_seen_minor
        if price >= seen:
            if price > seen:  # it went up: the next drop counts from here
                item.price_seen_minor = price
                item.save(update_fields=["price_seen_minor", "updated_at"])
            continue
        if (seen - price) * 100 < threshold * seen:
            continue
        if item.price_alerted_at and item.price_alerted_at > now - datetime.timedelta(days=days):
            continue
        language = getattr(item.user, "preferred_language", "") or "fr"
        notify(
            item.user,
            "shop.price_drop",
            {
                "product": product.title,
                "before": Money(seen, product.currency).format(language),
                "price": Money(price, product.currency).format(language),
            },
            link=product_link(product),
        )
        item.price_seen_minor = price
        item.price_alerted_at = now
        item.save(update_fields=["price_seen_minor", "price_alerted_at", "updated_at"])
        sent += 1
    return sent


def after_change(product_id, restocked: list, price_changed: bool) -> None:
    """After a pro changed a product: alerts for the stock and the price."""
    if restocked:
        notify_back_in_stock(restocked)
    if price_changed:
        check_price_drop(product_id)


def announce_flash_sales(now=None) -> int:
    """Celery Beat: a flash sale that just started may be a price drop for wishlists."""
    now = now or timezone.now()
    count = 0
    for sale in FlashSale.objects.filter(
        announced_at__isnull=True, starts_at__lte=now, ends_at__gt=now
    ):
        with transaction.atomic():
            updated = FlashSale.objects.filter(pk=sale.pk, announced_at__isnull=True).update(
                announced_at=now
            )
        if updated:
            check_price_drop(sale.product_id, now)
            count += 1
    return count
