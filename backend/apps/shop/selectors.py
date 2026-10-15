"""Reading the shops: what is on sale, a pro's own shop, orders and statistics."""

from __future__ import annotations

import datetime

from django.db.models import Count, Prefetch, Q, Sum
from django.utils import timezone

from apps.core.selectors import get_setting, is_feature_enabled
from apps.pros.models import ProProfile

from .models import Bundle, BundleItem, Order, OrderLine, Product, ShopProfile, Variant

S = Order.Status
LIVE = (S.NEW, S.PREPARING, S.SHIPPED, S.READY, S.DISPUTED)


def shop_enabled(country) -> bool:
    """The « shop » switch of the admin, per country."""
    return is_feature_enabled("shop", country=country)


def shop_of(pro: ProProfile) -> ShopProfile:
    shop, _ = ShopProfile.objects.get_or_create(pro=pro)
    return shop


def _with_details(products):
    return products.select_related(
        "pro", "pro__user", "category", "video", "description_voice"
    ).prefetch_related(
        Prefetch("variants", queryset=Variant.objects.order_by("position", "created_at")),
        Prefetch("photos__media"),
        "flash_sales",
    )


def on_sale():
    """Products anyone can see: online, not hidden by moderation, in a published showcase."""
    return Product.objects.filter(
        status=Product.Status.PUBLISHED,
        visibility="visible",
        pro__status=ProProfile.Status.PUBLISHED,
    )


def products_of_shop(pro: ProProfile, *, category: str | None = None):
    rows = on_sale().filter(pro=pro)
    if category:
        rows = rows.filter(category__key=category)
    return _with_details(rows).order_by("-published_at")


def products_in(product_ids):
    return _with_details(on_sale().filter(pk__in=product_ids))


def product_on_sale(product_id) -> Product | None:
    return _with_details(on_sale()).filter(pk=product_id).first()


def product_by_slug(pro_slug: str, product_slug: str) -> Product | None:
    return _with_details(on_sale()).filter(pro__slug=pro_slug, slug=product_slug).first()


def my_products(pro: ProProfile):
    return _with_details(
        Product.objects.filter(pro=pro).exclude(status=Product.Status.ARCHIVED)
    ).order_by("-created_at")


def my_product(pro: ProProfile, product_id) -> Product | None:
    return my_products(pro).filter(pk=product_id).first()


def bundles_on_sale(pro: ProProfile):
    return my_bundles(pro).filter(is_active=True)


def my_bundles(pro: ProProfile):
    return (
        Bundle.objects.filter(pro=pro)
        .select_related("photo")
        .prefetch_related(
            Prefetch(
                "items",
                queryset=BundleItem.objects.select_related("variant", "variant__product"),
            )
        )
    )


def bundle_is_sellable(bundle: Bundle) -> bool:
    items = list(bundle.items.all())
    return bool(items) and all(
        item.variant.is_active
        and item.variant.product.status == Product.Status.PUBLISHED
        and item.variant.product.visibility == "visible"
        for item in items
    )


def orders_of(user, *, role: str = "buyer", status: str | None = None):
    rows = Order.objects.select_related("pro", "pro__user", "buyer", "payment").prefetch_related(
        Prefetch("lines", queryset=OrderLine.objects.select_related("photo"))
    )
    rows = rows.filter(pro__user=user) if role == "seller" else rows.filter(buyer=user)
    if status == "active":
        rows = rows.filter(status__in=LIVE)
    elif status:
        rows = rows.filter(status=status)
    return rows.order_by("-created_at")


def order_for(user, order_id) -> Order | None:
    """An order of the client or of the seller, nobody else."""
    return (
        Order.objects.select_related("pro", "pro__user", "buyer", "payment", "shipping_proof")
        .prefetch_related(Prefetch("lines", queryset=OrderLine.objects.select_related("photo")))
        .filter(Q(buyer=user) | Q(pro__user=user), pk=order_id)
        .first()
    )


def stats(pro: ProProfile, *, days: int = 30) -> dict:
    """Simple numbers for « My shop »: orders, sales, best products, what runs out."""
    since = timezone.now() - datetime.timedelta(days=days)
    orders = Order.objects.filter(pro=pro, created_at__gte=since).exclude(
        status__in=[S.PENDING_PAYMENT, S.CANCELLED]
    )
    completed = orders.filter(status=S.COMPLETED)
    top = (
        OrderLine.objects.filter(order__in=orders, product__isnull=False)
        .values("product_id", "title")
        .annotate(quantity=Sum("quantity"), amount=Sum("total_minor"))
        .order_by("-quantity", "title")[:5]
    )
    low = int(get_setting("shop.low_stock_threshold", country=pro.country, default=3))
    running_out = (
        Variant.objects.filter(
            product__pro=pro,
            product__status=Product.Status.PUBLISHED,
            is_active=True,
            stock__lte=low,
        )
        .select_related("product")
        .order_by("stock")[:20]
    )
    to_handle = Order.objects.filter(pro=pro).aggregate(
        new=Count("pk", filter=Q(status=S.NEW)),
        preparing=Count("pk", filter=Q(status=S.PREPARING)),
    )
    return {
        "days": days,
        "currency": pro.currency,
        "orders": orders.count(),
        "sales_minor": orders.aggregate(total=Sum("items_minor"))["total"] or 0,
        "completed_minor": completed.aggregate(total=Sum("items_minor"))["total"] or 0,
        "new": to_handle["new"],
        "preparing": to_handle["preparing"],
        "top": [
            {
                "product_id": str(row["product_id"]),
                "title": row["title"],
                "quantity": row["quantity"],
                "amount_minor": row["amount"],
            }
            for row in top
        ],
        "running_out": running_out,
    }
