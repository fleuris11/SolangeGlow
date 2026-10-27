"""Sales lives (module 4, ADR-013): a verified shop plans a live, pins its products on air,
the viewers buy without leaving it (cart and grouped payment of the shop); every paid
order counts in the live. The replay stays `shop.live_replay_days` days, products too."""

from __future__ import annotations

import datetime

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.core.audit.services import record
from apps.core.selectors import get_setting, is_feature_enabled
from apps.pros.selectors import can_collect_payments

from .. import errors
from ..models import LivePin, Order, Product, SaleLive
from ..selectors import shop_enabled
from .catalog import pro_of

SL = SaleLive.Status
KIND = "sale"


def lives_open(country) -> bool:
    return shop_enabled(country) and is_feature_enabled("live_sales", country=country)


def _validate(values: dict, country) -> None:
    title = (values.get("title") or "").strip()
    starts_at = values.get("starts_at")
    duration = values.get("duration_minutes")
    longest = int(get_setting("live.max_minutes", country=country.code, default=120))
    if (
        not title
        or len(title) > 120
        or starts_at is None
        or starts_at <= timezone.now()
        or type(duration) is not int
        or not 15 <= duration <= longest
    ):
        raise errors.InvalidSaleLive(details={"max": longest})


@transaction.atomic
def plan(user, **values) -> SaleLive:
    pro = pro_of(user)
    if not lives_open(pro.country):
        raise errors.SaleLivesClosed()
    if not can_collect_payments(pro):
        raise errors.VerificationNeeded()
    _validate(values, pro.country)
    from apps.live.services import check_quota

    check_quota(pro, values["starts_at"])
    live = SaleLive.objects.create(
        pro=pro,
        title=values["title"].strip(),
        description=(values.get("description") or "").strip()[:500],
        starts_at=values["starts_at"],
        duration_minutes=values["duration_minutes"],
        currency=pro.currency,
    )
    record("shop.live_planned", live, actor=user)
    return live


def my_live(user, live_id) -> SaleLive:
    live = SaleLive.objects.filter(pk=live_id, pro=pro_of(user)).first()
    if live is None:
        raise errors.SaleLiveNotFound()
    return live


@transaction.atomic
def cancel(user, live_id) -> SaleLive:
    live = my_live(user, live_id)
    if live.status != SL.SCHEDULED:
        raise errors.SaleLiveNotFound()
    live.status = SL.CANCELLED
    live.save(update_fields=["status", "updated_at"])
    record("shop.live_cancelled", live, actor=user)
    return live


def _room(live: SaleLive):
    from apps.live.models import LiveRoom

    return LiveRoom.objects.filter(kind=KIND, source_id=live.pk).first()


def _push(live: SaleLive, kind: str, **data) -> None:
    from apps.live.services import push

    room = _room(live)
    if room is not None:
        push(room, kind, **data)


@transaction.atomic
def pin(user, live_id, product_id) -> LivePin:
    live = my_live(user, live_id)
    if live.status not in (SL.SCHEDULED, SL.LIVE):
        raise errors.SaleLiveNotFound()
    product = Product.objects.filter(
        pk=product_id, pro=live.pro, status=Product.Status.PUBLISHED, visibility="visible"
    ).first()
    if product is None:
        raise errors.ProductNotFound()
    now = timezone.now()
    found, _created = LivePin.objects.update_or_create(
        sale_live=live, product=product, defaults={"pinned_at": now, "unpinned_at": None}
    )
    _push(live, "pins")
    return found


@transaction.atomic
def unpin(user, live_id, product_id) -> None:
    live = my_live(user, live_id)
    LivePin.objects.filter(sale_live=live, product_id=product_id, unpinned_at=None).update(
        unpinned_at=timezone.now()
    )
    _push(live, "pins")


def sale_live_for_cart(sale_live_id, pro_id) -> SaleLive | None:
    """The live an item is added from, when it is the live of that shop (on air or replay)."""
    if not sale_live_id:
        return None
    return (
        SaleLive.objects.filter(pk=sale_live_id, pro_id=pro_id)
        .exclude(status__in=[SL.CANCELLED, SL.SCHEDULED])
        .first()
    )


def count_purchase(order: Order) -> None:
    """A paid order of the live: its counters go up, everybody in the room sees it."""
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        if order.sale_live_id is None or order.counted_in_live:
            return
        Order.objects.filter(pk=order.pk).update(counted_in_live=True)
        SaleLive.objects.filter(pk=order.sale_live_id).update(
            orders_count=F("orders_count") + 1,
            revenue_minor=F("revenue_minor") + order.items_minor,
        )
        live = SaleLive.objects.get(pk=order.sale_live_id)
        line = order.lines.order_by("created_at").first()
        _push(live, "purchase", product=line.title if line else "", count=live.orders_count)


def public_lives(pro, now=None) -> list[SaleLive]:
    """What the shop page shows: on air, coming, and the replays still visible."""
    now = now or timezone.now()
    days = int(get_setting("shop.live_replay_days", country=pro.country.code, default=7))
    since = now - datetime.timedelta(days=days)
    return list(
        SaleLive.objects.filter(pro=pro, starts_at__gte=since)
        .select_related("pro__country")
        .exclude(status=SL.CANCELLED)
        .order_by("-starts_at")[:10]
    )
