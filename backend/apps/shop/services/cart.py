"""The cart of a client: lines grouped by shop, with today's prices and stock."""

from __future__ import annotations

from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import Prefetch

from apps.accounts.selectors import can_purchase
from apps.core.selectors import get_setting

from .. import errors, prices
from ..models import Bundle, BundleItem, CartItem, FlashSale, Product, Variant
from ..selectors import bundle_is_sellable, shop_of


@dataclass
class CartLine:
    item: CartItem
    title: str
    variant_label: str
    photo: object
    product: Product | None
    bundle: Bundle | None
    unit_price_minor: int
    base_price_minor: int
    quantity: int
    stock_left: int
    available: bool
    flash_sale: FlashSale | None = None
    category_key: str = ""

    @property
    def total_minor(self) -> int:
        return self.unit_price_minor * self.quantity

    @property
    def enough(self) -> bool:
        return self.available and self.stock_left >= self.quantity

    def stock_needs(self) -> list[tuple]:
        """(variant id, quantity) taken from the stock by this line."""
        if self.bundle is not None:
            return [(i.variant_id, i.quantity * self.quantity) for i in self.bundle.items.all()]
        return [(self.item.variant_id, self.quantity)]


@dataclass
class CartShop:
    pro: object
    shop: object
    currency: str
    lines: list[CartLine] = field(default_factory=list)

    @property
    def subtotal_minor(self) -> int:
        return sum(line.total_minor for line in self.lines)

    @property
    def prep_days(self) -> int:
        return max(
            (line.product.prep_days for line in self.lines if line.product is not None), default=0
        )

    @property
    def category_key(self) -> str:
        """The category that weighs most in the order (it chooses the commission rule)."""
        weights: dict[str, int] = {}
        for line in self.lines:
            weights[line.category_key] = weights.get(line.category_key, 0) + line.total_minor
        return max(weights, key=weights.get) if weights else ""


def _on_sale(product: Product) -> bool:
    return (
        product.status == Product.Status.PUBLISHED
        and product.visibility == "visible"
        and product.pro.is_published
    )


def _variant_line(item: CartItem) -> CartLine:
    variant = item.variant
    product = variant.product
    sale = prices.active_flash_sale(product)
    photos = list(product.photos.all())
    return CartLine(
        item=item,
        title=product.title,
        variant_label=variant.label,
        photo=photos[0].media if photos else None,
        product=product,
        bundle=None,
        unit_price_minor=prices.unit_price(variant, sale),
        base_price_minor=variant.base_price_minor,
        quantity=item.quantity,
        stock_left=variant.stock,
        available=variant.is_active and _on_sale(product),
        flash_sale=sale,
        category_key=product.category.key if product.category_id else "",
    )


def _bundle_line(item: CartItem) -> CartLine:
    bundle = item.bundle
    first = next(iter(bundle.items.all()), None)
    category = first.variant.product.category if first else None
    return CartLine(
        item=item,
        title=bundle.title,
        variant_label="",
        photo=bundle.photo,
        product=None,
        bundle=bundle,
        unit_price_minor=bundle.price_minor,
        base_price_minor=prices.bundle_worth(bundle),
        quantity=item.quantity,
        stock_left=prices.bundle_stock(bundle),
        available=bundle.is_active and bundle.pro.is_published and bundle_is_sellable(bundle),
        category_key=category.key if category else "",
    )


def cart_summary(user) -> list[CartShop]:
    items = (
        CartItem.objects.filter(user=user)
        .select_related(
            "variant__product__pro__user",
            "variant__product__pro__country",
            "variant__product__category",
            "bundle__pro__user",
            "bundle__pro__country",
            "bundle__photo",
        )
        .prefetch_related(
            "variant__product__photos__media",
            "variant__product__flash_sales",
            Prefetch(
                "bundle__items",
                queryset=BundleItem.objects.select_related(
                    "variant__product__category", "variant__product__pro"
                ),
            ),
        )
        .order_by("created_at")
    )
    shops: dict = {}
    for item in items:
        line = _variant_line(item) if item.variant_id else _bundle_line(item)
        pro = line.product.pro if line.product is not None else line.bundle.pro
        if pro.pk not in shops:
            shops[pro.pk] = CartShop(pro=pro, shop=shop_of(pro), currency=pro.currency or "XOF")
        shops[pro.pk].lines.append(line)
    return list(shops.values())


def count(user) -> int:
    return CartItem.objects.filter(user=user).count()


def _max_quantity(pro) -> int:
    return int(get_setting("shop.max_quantity_per_line", country=pro.country, default=20))


@transaction.atomic
def add(user, *, variant_id=None, bundle_id=None, quantity: int = 1) -> CartItem:
    """Adds to the cart (or adds up). The stock is only taken when the order is placed."""
    if not can_purchase(user):
        raise errors.CannotBuy()
    if type(quantity) is not int or quantity < 1:
        maximum = int(get_setting("shop.max_quantity_per_line", default=20))
        raise errors.InvalidQuantity(details={"max": maximum})
    if variant_id:
        variant = Variant.objects.select_related("product__pro").filter(pk=variant_id).first()
        if variant is None or not variant.is_active or not _on_sale(variant.product):
            raise errors.ProductNotFound()
        pro, title, stock = variant.product.pro, variant.product.title, variant.stock
        lookup = {"variant": variant}
    else:
        bundle = (
            Bundle.objects.select_related("pro")
            .prefetch_related("items__variant__product")
            .filter(pk=bundle_id)
            .first()
        )
        if bundle is None or not bundle.is_active or not bundle_is_sellable(bundle):
            raise errors.ProductNotFound()
        pro, title, stock = bundle.pro, bundle.title, prices.bundle_stock(bundle)
        lookup = {"bundle": bundle}
    if pro.user_id == user.pk:
        raise errors.OwnShop()
    existing = CartItem.objects.select_for_update().filter(user=user, **lookup).first()
    wanted = quantity + (existing.quantity if existing else 0)
    maximum = _max_quantity(pro)
    if wanted > maximum:
        raise errors.InvalidQuantity(details={"max": maximum})
    if wanted > stock:
        raise errors.OutOfStock(details={"title": title, "left": stock})
    if existing is not None:
        existing.quantity = wanted
        existing.save(update_fields=["quantity", "updated_at"])
        return existing
    lines_max = int(get_setting("shop.cart_max_lines", default=30))
    if CartItem.objects.filter(user=user).count() >= lines_max:
        raise errors.CartFull(details={"max": lines_max})
    return CartItem.objects.create(user=user, quantity=quantity, **lookup)


def set_quantity(user, item_id, quantity: int) -> CartItem | None:
    """0 removes the line."""
    item = (
        CartItem.objects.select_related("variant__product__pro", "bundle__pro")
        .filter(pk=item_id, user=user)
        .first()
    )
    if item is None:
        raise errors.ProductNotFound()
    if quantity == 0:
        item.delete()
        return None
    pro = item.variant.product.pro if item.variant_id else item.bundle.pro
    maximum = _max_quantity(pro)
    if type(quantity) is not int or not 1 <= quantity <= maximum:
        raise errors.InvalidQuantity(details={"max": maximum})
    item.quantity = quantity
    item.save(update_fields=["quantity", "updated_at"])
    return item
