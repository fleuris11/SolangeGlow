"""Prices as the client sees them now: a flash sale lowers the price of every variant."""

from __future__ import annotations

from django.utils import timezone

from .models import FlashSale, Product, Variant


def percent_off(amount_minor: int, percent: int) -> int:
    """The amount after a discount, rounded half up to the smallest unit."""
    return (amount_minor * (100 - percent) * 2 + 100) // 200


def active_flash_sale(product: Product, now=None) -> FlashSale | None:
    now = now or timezone.now()
    sales = getattr(product, "_flash_sales", None)
    if sales is None:
        # .all() uses a prefetch when the caller made one.
        sales = [s for s in product.flash_sales.all() if s.ends_at > now]
        product._flash_sales = sales
    for sale in sales:
        if sale.starts_at <= now < sale.ends_at and (
            sale.quantity_limit is None or sale.sold_count < sale.quantity_limit
        ):
            return sale
    return None


def next_flash_sale(product: Product, now=None) -> FlashSale | None:
    now = now or timezone.now()
    active_flash_sale(product, now)
    upcoming = [s for s in product._flash_sales if s.starts_at > now]
    return min(upcoming, key=lambda s: s.starts_at) if upcoming else None


def unit_price(variant: Variant, sale: FlashSale | None) -> int:
    base = variant.base_price_minor
    return percent_off(base, sale.percent_off) if sale else base


def sellable_variants(product: Product) -> list[Variant]:
    return [v for v in product.variants.all() if v.is_active]


def lowest_price(product: Product, now=None) -> tuple[int, int]:
    """(price now, price before the flash sale) of the cheapest variant."""
    sale = active_flash_sale(product, now)
    variants = sellable_variants(product) or [Variant(product=product)]
    cheapest = min(variants, key=lambda v: v.base_price_minor)
    return unit_price(cheapest, sale), cheapest.base_price_minor


def in_stock(product: Product) -> bool:
    return any(v.stock > 0 for v in sellable_variants(product))


def bundle_stock(bundle) -> int:
    """How many bundles can be sold: the scarcest product decides."""
    counts = [item.variant.stock // item.quantity for item in bundle.items.all()]
    return min(counts) if counts else 0


def bundle_worth(bundle) -> int:
    """What the products of the bundle cost separately (to show the saving)."""
    return sum(item.variant.base_price_minor * item.quantity for item in bundle.items.all())
