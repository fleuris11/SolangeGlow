"""Sales lives in the live room (ADR-013): anyone may watch (an account is needed to buy
or write); the pinned products sit under the video; the replay is public a few days."""

from __future__ import annotations

import datetime

from django.db.models import Prefetch
from django.utils import timezone

from apps.core.selectors import get_setting
from apps.live import registry

from . import prices
from .models import LivePin, Product, ProductPhoto, SaleLive, Variant
from .serializers import _ready
from .services.lives import lives_open

SL = SaleLive.Status


def room_link(live_id) -> str:
    return f"/live/sale/{live_id}"


def _planned(live: SaleLive) -> registry.Planned:
    pro = live.pro
    return registry.Planned(
        source_id=live.pk,
        title=live.title,
        host=pro.user,
        pro=pro,
        country=pro.country,
        starts_at=live.starts_at,
        ends_at=live.starts_at + datetime.timedelta(minutes=live.duration_minutes),
        cancelled=live.status == SL.CANCELLED,
        link=f"/{pro.slug}/shop",
    )


def pin_payload(pin: LivePin) -> dict:
    product = pin.product
    price, _before = prices.lowest_price(product)
    photo = next(iter(product.photos.all()), None)
    return {
        "product_id": product.pk,
        "slug": product.slug,
        "name": product.title,
        "price_minor": price,
        "currency": product.currency,
        "photo": _ready(photo.media) if photo else None,
        "in_stock": product.status == Product.Status.PUBLISHED and prices.in_stock(product),
        "pinned": pin.unpinned_at is None,
    }


class SaleLives(registry.LiveSource):
    kind = "sale"
    hands = False
    guests = True

    def _get(self, source_id):
        return (
            SaleLive.objects.select_related("pro__user", "pro__country", "pro__photo")
            .filter(pk=source_id)
            .first()
        )

    def planned(self, source_id):
        live = self._get(source_id)
        return _planned(live) if live else None

    def can_watch(self, user, source_id) -> bool:
        return True

    def replay_days(self, country) -> int:
        return int(get_setting("shop.live_replay_days", country=country.code, default=7))

    def started(self, source_id, room) -> None:
        SaleLive.objects.filter(pk=source_id).update(status=SL.LIVE, updated_at=timezone.now())
        from .tasks import notify_live_followers

        notify_live_followers.delay(str(source_id))

    def ended(self, source_id, room) -> None:
        SaleLive.objects.filter(pk=source_id, status__in=[SL.SCHEDULED, SL.LIVE]).update(
            status=SL.ENDED, updated_at=timezone.now()
        )

    def extras(self, source_id, room, user) -> dict | None:
        live = self._get(source_id)
        if live is None:
            return None
        pins = (
            LivePin.objects.filter(sale_live=live)
            .select_related("product__pro")
            .prefetch_related(
                Prefetch("product__variants", queryset=Variant.objects.order_by("position")),
                Prefetch(
                    "product__photos",
                    queryset=ProductPhoto.objects.select_related("media").order_by("position"),
                ),
            )
        )
        host = user is not None and user.is_authenticated and live.pro.user_id == user.pk
        ordered = sorted(
            pins, key=lambda pin: (pin.unpinned_at is not None, -pin.pinned_at.timestamp())
        )
        return {
            "shop_slug": live.pro.slug,
            "pins": [pin_payload(pin) for pin in ordered],
            "orders_count": live.orders_count,
            "revenue_minor": live.revenue_minor if host else None,
            "currency": live.currency,
        }

    def upcoming(self, country, now, limit: int):
        if country is None or not lives_open(country):
            return []
        rows = (
            SaleLive.objects.filter(
                pro__country=country,
                status__in=[SL.SCHEDULED, SL.LIVE],
                starts_at__gte=now - datetime.timedelta(hours=6),
            )
            .select_related("pro__user", "pro__country", "pro__photo")
            .order_by("starts_at")[: limit * 2]
        )
        return [
            _planned(live)
            for live in rows
            if live.starts_at + datetime.timedelta(minutes=live.duration_minutes) > now
        ][:limit]

    def count_in_month(self, pro, start, end) -> int:
        return (
            SaleLive.objects.filter(pro=pro, starts_at__gte=start, starts_at__lt=end)
            .exclude(status=SL.CANCELLED)
            .count()
        )


def _rooms(lives) -> dict:
    from apps.live.models import LiveRoom

    rows = LiveRoom.objects.filter(kind="sale", source_id__in=[live.pk for live in lives])
    return {room.source_id: room for room in rows}


def _replay_ready(room, now) -> bool:
    from apps.live.models import LiveRoom

    return bool(
        room
        and room.replay_status == LiveRoom.Replay.READY
        and (room.replay_until is None or room.replay_until > now)
    )


def public_payloads(lives) -> list[dict]:
    """The lives of a shop page: on air, coming, replays still visible."""
    now = timezone.now()
    rooms = _rooms(lives)
    result = []
    for live in lives:
        room = rooms.get(live.pk)
        replay = _replay_ready(room, now)
        if live.status == SL.ENDED and not replay:
            continue
        result.append(
            {
                "id": live.pk,
                "title": live.title,
                "starts_at": live.starts_at,
                "status": live.status,
                "replay": replay,
                "link": room_link(live.pk),
                "time_zone": live.pro.country.timezone,
            }
        )
    return result


def my_payloads(lives) -> list[dict]:
    now = timezone.now()
    rooms = _rooms(lives)
    result = []
    for live in lives:
        room = rooms.get(live.pk)
        result.append(
            {
                "id": live.pk,
                "title": live.title,
                "description": live.description,
                "starts_at": live.starts_at,
                "duration_minutes": live.duration_minutes,
                "status": live.status,
                "orders_count": live.orders_count,
                "revenue_minor": live.revenue_minor,
                "currency": live.currency,
                "peak_viewers": room.peak_viewers if room else 0,
                "total_viewers": room.total_viewers if room else 0,
                "replay": _replay_ready(room, now),
                "link": room_link(live.pk),
                "time_zone": live.pro.country.timezone,
            }
        )
    return result
