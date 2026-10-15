"""What the shop gives to the other modules (registered in ShopConfig.ready):

- verified reviews: a handed-over order opens the right to review the pro (« order »);
- messaging: a product card in a conversation, and no « Pay in the app » warning between
  two people who already dealt through an order (done by the payments module);
- social: « Buy this product » on a post of the pro.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable

from django.utils import formats

from apps.core.media.services import asset_payload
from apps.social.eligibility import Transaction

from . import prices
from .models import Order, Product
from .selectors import on_sale


def _transaction(order: Order) -> Transaction:
    finished = order.completed_at if order.status == Order.Status.COMPLETED else None
    titles = ", ".join(line.title for line in order.lines.all()[:2])
    when = formats.date_format(order.created_at, "j F")
    return Transaction(
        kind="order",
        id=order.pk,
        client_id=order.buyer_id,
        pro_id=order.pro_id,
        finished_at=finished,
        label=f"{titles}, {when}"[:120],
    )


class OrderEligibility:
    """A handed-over order of the client: she can review the pro, the pro can rate her."""

    kind = "order"

    def get(self, transaction_id: uuid.UUID) -> Transaction | None:
        order = Order.objects.prefetch_related("lines").filter(pk=transaction_id).first()
        return _transaction(order) if order else None

    def finished_for_client(self, client_id: uuid.UUID) -> Iterable[Transaction]:
        orders = Order.objects.filter(buyer_id=client_id, status=Order.Status.COMPLETED)
        return [_transaction(o) for o in orders.prefetch_related("lines")[:50]]

    def finished_for_pro(self, pro_id: uuid.UUID) -> Iterable[Transaction]:
        orders = Order.objects.filter(pro_id=pro_id, status=Order.Status.COMPLETED)
        return [_transaction(o) for o in orders.prefetch_related("lines")[:50]]


def product_card(product: Product) -> dict:
    photo = next(iter(product.photos.all()), None)
    price, before = prices.lowest_price(product)
    return {
        "id": str(product.pk),
        "title": product.title,
        "price_minor": price,
        "before_minor": before if before != price else None,
        "currency": product.currency,
        "picture": asset_payload(photo.media) if photo and photo.media.is_ready else None,
        "in_stock": prices.in_stock(product),
        "link": f"/{product.pro.slug}/shop/{product.slug}",
    }


def _cards_query():
    return (
        on_sale().select_related("pro").prefetch_related("photos__media", "variants", "flash_sales")
    )


def share_product(sender, data: dict):
    """Messaging resolver: (id, card) of a product on sale."""
    from apps.messaging import errors as messaging_errors

    try:
        product_id = uuid.UUID(str(data.get("id")))
    except ValueError as exc:
        raise messaging_errors.ShareNotFound() from exc
    product = _cards_query().filter(pk=product_id).first()
    if product is None:
        raise messaging_errors.ShareNotFound()
    card = product_card(product)
    return product.pk, {
        "title": card["title"],
        "text": product.pro.display_name,
        "picture": card["picture"],
        "amount_minor": card["price_minor"],
        "currency": card["currency"],
        "link": card["link"],
    }


def owns_product(author, product_id) -> bool:
    """Social: a pro links one of her own products (online) to a post."""
    return on_sale().filter(pk=product_id, pro__user=author).exists()


def post_product_card(product_id) -> dict | None:
    product = _cards_query().filter(pk=product_id).first()
    return product_card(product) if product else None
