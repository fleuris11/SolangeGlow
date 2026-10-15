"""Shops, products and orders for the tests (Bénin, FCFA).

Example used in most tests: a foundation at 8 000 FCFA, delivery 1 000 FCFA, buyer
protection 3 % of 9 000 = 270, total 9 270.
"""

from apps.core.media.models import MediaAsset
from apps.messaging.tests.factories import adult, upload
from apps.payments.services import groups as group_services
from apps.payments.tests.factories import seller
from apps.shop.models import DeliveryZone, Order
from apps.shop.selectors import shop_of
from apps.shop.services import cart, catalog, checkout


def shop_owner(name="Gloria Make-up", **kwargs):
    """A verified pro (her account)."""
    return seller(name, **kwargs)


def photo(owner, purpose="product_photo", status=MediaAsset.Status.READY):
    return upload(owner, purpose=purpose, status=status)


def product(
    owner=None,
    *,
    title="Fond de teint Velours",
    price=8_000,
    stock=10,
    variants=None,
    category="makeup",
    publish=True,
    prep_days=1,
    description="Tenue 12 heures, fini mat.",
):
    owner = owner or shop_owner()
    created = catalog.save_product(
        owner,
        title=title,
        price_minor=price,
        category_key=category,
        description=description,
        prep_days=prep_days,
        photo_ids=[photo(owner).pk],
        variants=variants if variants is not None else [{"stock": stock}],
    )
    if publish:
        catalog.publish(owner, created)
        created.refresh_from_db()
    return created


def delivers(owner, *, mode="seller", name="Cotonou centre", fee=1_000) -> DeliveryZone:
    catalog.update_shop(
        owner, **({"seller_delivery": True} if mode == "seller" else {"partner_delivery": True})
    )
    if mode == "partner":
        catalog.update_shop(owner, partner_name="Gozem")
    return catalog.save_zone(owner, mode=mode, name=name, fee_minor=fee)


def buyer(name="Awa"):
    return adult(name)


def choice(owner, mode="pickup", zone=None, promo="", note=""):
    return checkout.ShopChoice(
        pro_id=owner.pro_profile.pk,
        delivery_mode=mode,
        zone_id=zone.pk if zone else None,
        promo_code=promo,
        note=note,
    )


def order(client=None, item=None, *, quantity=1, mode="pickup", zone=None, promo="", paid=True):
    """An order of one product (placed and, by default, paid through its group)."""
    client = client or buyer()
    item = item or product()
    owner = item.pro.user
    if mode != "pickup" and zone is None:
        zone = delivers(owner, mode=mode)
    cart.add(client, variant_id=item.variants.first().pk, quantity=quantity)
    group, orders = checkout.place_orders(
        client,
        [choice(owner, mode, zone, promo)],
        address="Rue 12.345, Fidjrossè",
        phone="+2290197123456",
    )
    if paid:
        pay(group)
    placed = Order.objects.get(pk=orders[0].pk)
    return placed


def pay(group, fee=0):
    group_services.mark_group_paid(
        group, amount_minor=group.total_minor, currency=group.currency, fee_minor=fee, key="t"
    )


def receipt_code(o: Order) -> str:
    from apps.payments.services import receipt_code_for

    return receipt_code_for(o.payment, o.buyer)


__all__ = ["shop_of"]
