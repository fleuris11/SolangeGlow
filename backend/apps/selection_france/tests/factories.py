"""Catalogue, pick-up points and orders of the France Selection for the tests.

Reference product (makeup, default parameters): 20.00 € bought, 300 g
-> 25 300 FCFA grouped, 29 100 FCFA express (see test_pricing).
"""

from apps.messaging.tests.factories import adult
from apps.payments import services as payment_services
from apps.selection_france import services
from apps.selection_france.models import PickupPoint, SelectionCategory, SelectionProduct


def category(key="makeup"):
    return SelectionCategory.objects.get(key=key)


def product(**kwargs) -> SelectionProduct:
    values = {
        "title": "Fond de teint Fenty",
        "slug": "fond-de-teint-fenty",
        "merchant_name": "Sephora",
        "merchant_url": "https://www.sephora.fr/fenty",
        "purchase_price_cents": 2000,
        "weight_grams": 300,
        "aisle": "trending",
        "category": category(),
    }
    values.update(kwargs)
    created = SelectionProduct.objects.create(**values)
    return services.reprice(created)


def point(name="Solange Glow Cotonou", city="Cotonou"):
    return PickupPoint.objects.create(name=name, city=city, address="Haie Vive, rue 12")


def client(name="Awa"):
    return adult(name)


def order(buyer=None, item=None, *, mode="grouped", quantity=1, paid=True, **kwargs):
    buyer = buyer or client()
    item = item or product()
    placed = services.place_order(
        buyer,
        item.pk,
        shipping_mode=mode,
        pickup_point_id=kwargs.pop("pickup", None) or point().pk,
        quantity=quantity,
        **kwargs,
    )
    if paid:
        pay(placed)
    placed.refresh_from_db()
    return placed


def pay(placed):
    payment = placed.payment
    payment_services.mark_paid(
        payment, amount_minor=payment.total_minor, currency="XOF", key=f"t:{payment.pk}"
    )


def code_of(placed) -> str:
    return payment_services.receipt_code_for(placed.payment, placed.buyer)
