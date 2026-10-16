"""Reading the France Selection: the house account, the catalogue, delays, orders."""

from __future__ import annotations

import datetime

from django.contrib.auth import get_user_model
from django.db.models import Prefetch, Sum
from django.utils import timezone

from apps.core.models import Country
from apps.core.selectors import get_setting, is_feature_enabled

from .models import (
    GroupBuy,
    PickupPoint,
    SelectionOrder,
    SelectionPhoto,
    SelectionProduct,
    ShippingMode,
)

O = SelectionOrder.Status  # noqa: E741
COUNTED = (O.WAITING_GROUP, O.TO_ORDER, O.ORDERED, O.RECEIVED, O.SHIPPED, O.ARRIVED, O.COMPLETED)

DEFAULT_DELAYS = {
    "purchase_days": [3, 6],
    "grouped_transit_days": [7, 12],
    "express_transit_days": [3, 5],
    "departure_weekday": 4,
}


def house_account():
    """The seller of every Selection order: the platform itself (created the first time)."""
    User = get_user_model()
    email = get_setting("selection.house_email", default="selection@solangeglow.com")
    user = User.objects.filter(email=email).first()
    if user is None:
        user = User.objects.create_user(
            email=email,
            first_name="Solange Glow Sélection",
            country=Country.objects.filter(code="BJ").first(),
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user


def selection_enabled(country) -> bool:
    return is_feature_enabled("selection", country=country)


def blocks_air_restricted() -> bool:
    return bool(get_setting("selection.block_air_restricted", default=True))


def on_sale():
    """Products clients see: not hidden, in an active category, not blocked by air rules."""
    rows = SelectionProduct.objects.filter(category__is_active=True).exclude(
        availability=SelectionProduct.Availability.HIDDEN
    )
    if blocks_air_restricted():
        rows = rows.exclude(category__air_restricted=True)
    return rows.select_related("category").prefetch_related(
        Prefetch("photos", queryset=SelectionPhoto.objects.select_related("media")),
        Prefetch("group_buys", queryset=GroupBuy.objects.filter(status=GroupBuy.Status.OPEN)),
    )


def open_group(product) -> GroupBuy | None:
    now = timezone.now()
    groups = [g for g in product.group_buys.all() if g.status == GroupBuy.Status.OPEN]
    return next((g for g in groups if g.ends_at > now), None)


def group_count(group: GroupBuy) -> int:
    total = SelectionOrder.objects.filter(group_buy=group, status__in=COUNTED).aggregate(
        total=Sum("quantity")
    )["total"]
    return total or 0


def pickup_points():
    return PickupPoint.objects.filter(is_active=True)


def delays() -> dict:
    return {**DEFAULT_DELAYS, **(get_setting("selection.delays", default={}) or {})}


def _next_departure(day: datetime.date, weekday: int) -> datetime.date:
    return day + datetime.timedelta(days=(weekday - day.weekday()) % 7)


def estimate(mode: str, today: datetime.date | None = None, *, after: datetime.date | None = None):
    """(first, last) day the parcel should be at the pick-up point.

    Grouped: bought in France, then the next weekly departure, then the transit.
    `after`: nothing is bought before this day (a group pre-order that is still open).
    """
    today = today or timezone.localdate()
    start = max(today, after) if after else today
    d = delays()
    buy_min, buy_max = (int(x) for x in d["purchase_days"])
    if mode == ShippingMode.EXPRESS:
        low, high = (int(x) for x in d["express_transit_days"])
        return (
            start + datetime.timedelta(days=buy_min + low),
            start + datetime.timedelta(days=buy_max + high),
        )
    low, high = (int(x) for x in d["grouped_transit_days"])
    weekday = int(d["departure_weekday"])
    first = _next_departure(start + datetime.timedelta(days=buy_min), weekday)
    last = _next_departure(start + datetime.timedelta(days=buy_max), weekday)
    return first + datetime.timedelta(days=low), last + datetime.timedelta(days=high)


def prep_days(mode: str, *, after: datetime.date | None = None) -> int:
    """Days before the departure from France (the secure payment waits this long)."""
    d = delays()
    buy_max = int(d["purchase_days"][1])
    extra = (after - timezone.localdate()).days if after else 0
    return max(extra, 0) + buy_max + (0 if mode == ShippingMode.EXPRESS else 7)


def orders_of(user):
    return (
        SelectionOrder.objects.filter(buyer=user)
        .select_related("payment", "pickup_point", "shipment", "product")
        .prefetch_related("product__photos__media")
        .order_by("-created_at")
    )


def order_for(user, order_id) -> SelectionOrder | None:
    return orders_of(user).filter(pk=order_id).first()
