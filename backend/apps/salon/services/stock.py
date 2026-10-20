"""Stock of the salon (Premium): products sold and used in the salon, barcodes, movements,
what each service uses, alerts before running out, inventory.

An item linked to a product of the shop shares its stock with it (no double count).
"""

from __future__ import annotations

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.core.audit.services import record
from apps.glowpro import selectors as glowpro
from apps.glowpro.models import Feature
from apps.notifications.services import notify
from apps.pros.models import Service

from .. import errors
from ..models import ServiceConsumption, StockItem, StockMovement

K = StockMovement.Kind


def _clean_ean(value: str) -> str:
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    if value and (len(digits) not in (8, 12, 13, 14) or not ean_ok(digits)):
        raise errors.InvalidStockItem()
    return digits


def ean_ok(digits: str) -> bool:
    """The check digit of EAN-8, UPC-A, EAN-13 and GTIN-14."""
    body, check = digits[:-1], int(digits[-1])
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(body)))
    return (10 - total % 10) % 10 == check


@transaction.atomic
def save_item(pro, *, item_id=None, actor=None, **values) -> StockItem:
    glowpro.require(pro, Feature.STOCK)
    name = (values.get("name") or "").strip()[:120]
    if not name or values.get("kind") not in StockItem.Kind.values:
        raise errors.InvalidStockItem()
    ean = _clean_ean(values.get("ean", ""))
    item = StockItem.objects.filter(pk=item_id, pro=pro).first() if item_id else StockItem(pro=pro)
    if item is None:
        raise errors.NotFound()
    if ean and StockItem.objects.filter(pro=pro, ean=ean).exclude(pk=item.pk).exists():
        raise errors.BarcodeTaken()
    new = item._state.adding
    item.name, item.ean, item.kind = name, ean, values["kind"]
    item.unit = values.get("unit") or item.unit or StockItem.Unit.PIECE
    item.alert_threshold = int(values.get("alert_threshold") or 0)
    item.cost_minor = values.get("cost_minor")
    variant_id = values.get("variant_id")
    if variant_id is not None:
        from apps.shop.models import Variant

        variant = (
            Variant.objects.filter(pk=variant_id, product__pro=pro).first() if variant_id else None
        )
        if variant_id and variant is None:
            raise errors.NotFound()
        item.variant = variant
        if variant is not None:
            item.quantity = variant.stock
    item.save()
    start = values.get("quantity")
    if new and start:
        move(item, int(start), K.IN, actor=actor)
        item.refresh_from_db()
    return item


def find_by_ean(pro, ean: str) -> StockItem | None:
    digits = "".join(ch for ch in (ean or "") if ch.isdigit())
    return StockItem.objects.filter(pro=pro, ean=digits).first() if digits else None


@transaction.atomic
def move(item: StockItem, change: int, kind: str, *, actor=None, appointment=None, note=""):
    """Adds or removes; the linked shop product moves with it. Returns the movement."""
    if type(change) is not int or change == 0 or kind not in K.values:
        raise errors.InvalidMovement()
    item = StockItem.objects.select_for_update().get(pk=item.pk)
    if item.variant_id:
        from apps.shop.models import Variant

        Variant.objects.filter(pk=item.variant_id).update(stock=F("stock") + change)
        item.quantity = Variant.objects.values_list("stock", flat=True).get(pk=item.variant_id)
    else:
        item.quantity += change
    item.save(update_fields=["quantity", "updated_at"])
    movement = StockMovement.objects.create(
        item=item,
        kind=kind,
        change=change,
        after=item.quantity,
        appointment=appointment,
        note=(note or "")[:120],
        actor=actor,
    )
    _alert(item)
    return movement


@transaction.atomic
def count(item: StockItem, counted: int, *, actor=None) -> StockMovement | None:
    """Inventory: the counted quantity becomes the stock; the difference is kept."""
    if type(counted) is not int or counted < 0:
        raise errors.InvalidMovement()
    item = StockItem.objects.select_for_update().get(pk=item.pk)
    difference = counted - item.quantity
    if difference == 0:
        return None
    return move(item, difference, K.INVENTORY, actor=actor)


def _alert(item: StockItem) -> None:
    today = timezone.localdate()
    if item.quantity > item.alert_threshold or item.alerted_on == today or not item.is_active:
        return
    item.alerted_on = today
    item.save(update_fields=["alerted_on", "updated_at"])
    pro = item.pro
    transaction.on_commit(
        lambda: notify(
            pro.user,
            "salon.stock_low",
            {"item": item.name, "quantity": item.quantity, "unit": item.get_unit_display()},
            link="/pro/stock",
        )
    )


@transaction.atomic
def set_consumption(pro, service_id, rows: list[dict]) -> Service:
    """What a service uses: [{item_id, quantity}] (replaces the list)."""
    glowpro.require(pro, Feature.STOCK)
    service = Service.objects.filter(pk=service_id, pro=pro).first()
    if service is None:
        raise errors.NotFound()
    items = {str(i.pk): i for i in StockItem.objects.filter(pro=pro)}
    ServiceConsumption.objects.filter(service=service).delete()
    for row in rows:
        item = items.get(str(row.get("item_id")))
        quantity = row.get("quantity")
        if item is None or type(quantity) is not int or quantity <= 0:
            raise errors.InvalidMovement()
        ServiceConsumption.objects.create(service=service, item=item, quantity=quantity)
    return service


def on_completed(appointment) -> None:
    """A done appointment takes from the stock what its service uses."""
    if StockMovement.objects.filter(appointment=appointment, kind=K.USE).exists():
        return
    for use in ServiceConsumption.objects.filter(service_id=appointment.service_id).select_related(
        "item"
    ):
        if use.item.is_active:
            move(
                use.item, -use.quantity, K.USE, appointment=appointment, note=appointment.reference
            )
    record("salon.stock_used", appointment)


def low_items(pro):
    return StockItem.objects.filter(
        pro=pro, is_active=True, quantity__lte=F("alert_threshold")
    ).order_by("quantity")
