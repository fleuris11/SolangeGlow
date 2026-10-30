"""The home page of the admin: the figures of the platform per country and period, with
their charts. Money is never added across currencies (FCFA and euros side by side)."""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.core.models import Country
from apps.core.money import Money

PERIODS = {"7": 7, "30": 30, "90": 90}


@dataclass(frozen=True)
class Window:
    start: datetime.datetime
    end: datetime.datetime
    previous_start: datetime.datetime
    country: str

    @property
    def days(self) -> int:
        return max(1, (self.end - self.start).days)


def window_of(params, now=None) -> Window:
    now = now or timezone.now()
    period = params.get("period", "30")
    if period == "month":
        start = timezone.localtime(now).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now - datetime.timedelta(days=PERIODS.get(period, 30))
    length = now - start
    country = (params.get("country") or "").upper()[:2]
    return Window(start=start, end=now, previous_start=start - length, country=country)


def _in(qs, field: str, start, end):
    return qs.filter(**{f"{field}__gte": start, f"{field}__lt": end})


def _count(qs, field, window: Window) -> tuple[int, int]:
    return (
        _in(qs, field, window.start, window.end).count(),
        _in(qs, field, window.previous_start, window.start).count(),
    )


def _country(qs, path: str, window: Window):
    return qs.filter(**{path: window.country}) if window.country else qs


def figures(window: Window) -> dict:
    from apps.accounts.models import LoginEvent
    from apps.booking.models import Appointment
    from apps.moderation.models import ModerationCase
    from apps.payments.models import Dispute, Payment
    from apps.selection_france.models import SelectionOrder
    from apps.shop.models import Order

    User = get_user_model()
    users = _country(User.objects.filter(is_staff=False), "country__code", window)
    signups = _count(users, "created_at", window)
    logins = _country(LoginEvent.objects.filter(success=True), "user__country__code", window)
    active = (
        _in(logins, "created_at", window.start, window.end).values("user").distinct().count(),
        _in(logins, "created_at", window.previous_start, window.start)
        .values("user")
        .distinct()
        .count(),
    )
    orders_qs = _country(
        Order.objects.exclude(status__in=[Order.Status.PENDING_PAYMENT, Order.Status.CANCELLED]),
        "buyer__country__code",
        window,
    )
    selection_qs = _country(
        SelectionOrder.objects.filter(payment__paid_at__isnull=False),
        "buyer__country__code",
        window,
    )
    shop_orders = _count(orders_qs, "created_at", window)
    selection_orders = _count(selection_qs, "created_at", window)
    bookings = _count(
        _country(
            Appointment.objects.exclude(
                status__in=[Appointment.Status.DECLINED, Appointment.Status.EXPIRED]
            ),
            "pro__country__code",
            window,
        ),
        "created_at",
        window,
    )
    payments = _country(
        Payment.objects.filter(paid_at__isnull=False), "buyer__country__code", window
    )
    sales = (
        _in(payments, "paid_at", window.start, window.end)
        .values("currency")
        .annotate(
            total=Sum("total_minor"),
            earned=Sum("commission_minor") + Sum("buyer_fee_minor"),
            count=Count("id"),
        )
        .order_by("currency")
    )
    S = Payment.Status
    held = (
        _country(Payment.objects, "buyer__country__code", window)
        .filter(status__in=[S.HELD, S.SHIPPED, S.DISPUTED])
        .values("currency")
        .annotate(total=Sum("total_minor"), count=Count("id"))
        .order_by("currency")
    )
    return {
        "signups": signups,
        "active": active,
        "orders": (shop_orders[0] + selection_orders[0], shop_orders[1] + selection_orders[1]),
        "bookings": bookings,
        "sales": list(sales),
        "held": list(held),
        "disputes": Dispute.objects.filter(status=Dispute.Status.OPEN).count(),
        "moderation": ModerationCase.objects.filter(status=ModerationCase.Status.PENDING).count(),
    }


def _series(qs, field: str, window: Window, value=None) -> list:
    rows = (
        _in(qs, field, window.start, window.end)
        .annotate(day=TruncDate(field))
        .values("day")
        .annotate(n=value or Count("id"))
        .order_by("day")
    )
    by_day = {row["day"]: row["n"] or 0 for row in rows}
    first = timezone.localtime(window.start).date()
    days = [first + datetime.timedelta(days=i) for i in range(window.days + 1)]
    return [(day, by_day.get(day, 0)) for day in days]


def charts(window: Window) -> dict:
    from apps.payments.models import Payment

    User = get_user_model()
    signups = _series(
        _country(User.objects.filter(is_staff=False), "country__code", window), "created_at", window
    )
    currency = "EUR" if window.country == "FR" else "XOF"
    paid = _country(
        Payment.objects.filter(paid_at__isnull=False, currency=currency),
        "buyer__country__code",
        window,
    )
    sales = _series(paid, "paid_at", window, value=Sum("total_minor"))
    divisor = 100 if currency == "EUR" else 1
    labels = [day.strftime("%d/%m") for day, _n in signups]
    return {
        "signups": json.dumps(
            {
                "labels": labels,
                "datasets": [
                    {
                        "label": _("Sign-ups"),
                        "data": [n for _d, n in signups],
                        "borderColor": "#C8102E",
                        "backgroundColor": "#C8102E",
                    }
                ],
            }
        ),
        "sales": json.dumps(
            {
                "labels": [day.strftime("%d/%m") for day, _n in sales],
                "datasets": [
                    {
                        "label": _("Sales paid (%(currency)s)") % {"currency": currency},
                        "data": [round(n / divisor, 2) for _d, n in sales],
                        "backgroundColor": "#E8B04B",
                    }
                ],
            }
        ),
        "currency": currency,
    }


def _trend(pair: tuple[int, int]) -> dict:
    now, before = pair
    change = None if before == 0 else round((now - before) * 100 / before)
    return {"value": now, "before": before, "change": change}


def _money(rows, key: str) -> list[str]:
    return [Money(int(row[key] or 0), row["currency"]).format("fr") for row in rows]


def dashboard_callback(request, context: dict) -> dict:
    """Unfold DASHBOARD_CALLBACK: the context of admin/index.html."""
    user = request.user
    if not (user.is_superuser or user.has_perm("backoffice.view_dashboard")):
        context.update({"show_dashboard": False})
        return context
    window = window_of(request.GET)
    found = figures(window)
    context.update(
        {
            "show_dashboard": True,
            "period": request.GET.get("period", "30"),
            "country": window.country,
            "countries": list(Country.objects.filter(is_active=True).values_list("code", "name")),
            "kpis": [
                {"title": _("Sign-ups"), **_trend(found["signups"]), "icon": "person_add"},
                {"title": _("Active people"), **_trend(found["active"]), "icon": "group"},
                {"title": _("Orders"), **_trend(found["orders"]), "icon": "shopping_bag"},
                {"title": _("Appointments"), **_trend(found["bookings"]), "icon": "event"},
            ],
            "sales": [
                {
                    "currency": row["currency"],
                    "total": total,
                    "earned": earned,
                    "count": row["count"],
                }
                for row, total, earned in zip(
                    found["sales"],
                    _money(found["sales"], "total"),
                    _money(found["sales"], "earned"),
                    strict=True,
                )
            ],
            "held": [
                {"currency": row["currency"], "total": total, "count": row["count"]}
                for row, total in zip(found["held"], _money(found["held"], "total"), strict=True)
            ],
            "queues": [
                {
                    "title": _("Open disputes"),
                    "value": found["disputes"],
                    "icon": "gavel",
                    "link": reverse("admin:backoffice_disputes_console"),
                },
                {
                    "title": _("Moderation queue"),
                    "value": found["moderation"],
                    "icon": "shield",
                    "link": reverse("admin:backoffice_moderation_console"),
                },
            ],
            "charts": charts(window),
        }
    )
    return context
