"""Monthly rankings of the pros, per city and trade, on the verified reviews of the month.

A review exists only after a finished appointment or order (verified). The score is a
weighted average: a pro with two 5-star reviews does not pass one with forty 4.8 ones.
"""

from __future__ import annotations

import datetime
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Avg, Count, Sum
from django.utils import timezone

from apps.pros.models import ProProfile
from apps.social.models import Review, Visibility

from ..models import Ranking
from .common import setting

TWO = Decimal("0.01")


def first_of(day: datetime.date) -> datetime.date:
    return day.replace(day=1)


def previous_month(day: datetime.date) -> datetime.date:
    return first_of(first_of(day) - datetime.timedelta(days=1))


def _bounds(month: datetime.date):
    start = timezone.make_aware(datetime.datetime.combine(month, datetime.time.min))
    following = first_of(month + datetime.timedelta(days=32))
    end = timezone.make_aware(datetime.datetime.combine(following, datetime.time.min))
    return start, end


@transaction.atomic
def compute(month: datetime.date) -> int:
    """(Re)computes the rankings of a month. Returns the number of rows."""
    month = first_of(month)
    start, end = _bounds(month)
    reviews = Review.objects.filter(
        visibility=Visibility.VISIBLE, created_at__gte=start, created_at__lt=end
    )
    overall = reviews.aggregate(average=Avg("rating"))["average"] or 0
    prior = int(setting("games.ranking_prior", 5))
    least = int(setting("games.ranking_min_reviews", 3))
    size = int(setting("games.ranking_size", 10))
    per_pro = {
        row["pro"]: row
        for row in reviews.values("pro").annotate(n=Count("id"), total=Sum("rating"))
        if row["n"] >= least
    }
    pros = (
        ProProfile.objects.filter(pk__in=per_pro, status=ProProfile.Status.PUBLISHED)
        .exclude(city="")
        .prefetch_related("trades")
    )
    groups = defaultdict(list)
    for pro in pros:
        row = per_pro[pro.pk]
        score = (Decimal(prior) * Decimal(overall) + row["total"]) / (prior + row["n"])
        average = Decimal(row["total"]) / row["n"]
        for trade in pro.trades.all():
            groups[(pro.city.strip(), trade.pk)].append((score, row["n"], average, pro))
    Ranking.objects.filter(month=month).delete()
    rows = []
    for (city, trade_id), found in groups.items():
        found.sort(key=lambda item: (-item[0], -item[1], str(item[3].pk)))
        for position, (score, count, average, pro) in enumerate(found[:size], start=1):
            rows.append(
                Ranking(
                    month=month,
                    city=city,
                    trade_id=trade_id,
                    pro=pro,
                    position=position,
                    score=score.quantize(TWO, ROUND_HALF_UP),
                    average=average.quantize(TWO, ROUND_HALF_UP),
                    reviews=count,
                )
            )
    Ranking.objects.bulk_create(rows)
    return len(rows)


def ensure_last_month(now=None) -> int:
    """Celery Beat, every day: the previous month is computed once it is over."""
    month = previous_month(timezone.localdate(now))
    if Ranking.objects.filter(month=month).exists():
        return 0
    return compute(month)


def latest_month() -> datetime.date | None:
    return Ranking.objects.order_by("-month").values_list("month", flat=True).first()


def table(*, month: datetime.date, city: str, trade_id):
    return (
        Ranking.objects.filter(month=month, city__iexact=city, trade_id=trade_id)
        .select_related("pro__user", "pro__photo", "trade")
        .order_by("position")
    )


def choices(month: datetime.date) -> dict:
    rows = Ranking.objects.filter(month=month)
    return {
        "cities": sorted(set(rows.values_list("city", flat=True))),
        "trades": sorted(set(rows.values_list("trade_id", flat=True)), key=str),
    }
