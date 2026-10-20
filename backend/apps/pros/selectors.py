from django.db.models import Count, Prefetch, Q, QuerySet

from apps.core.selectors import get_setting

from .models import (
    Closure,
    OpeningPeriod,
    PortfolioItem,
    ProProfile,
    Service,
    ServiceCategory,
    Trade,
)


def active_trades():
    return Trade.objects.filter(is_active=True).order_by("position", "key")


def visible_services() -> QuerySet[Service]:
    return (
        Service.objects.filter(is_active=True, archived_at__isnull=True)
        .select_related("trade", "category")
        .prefetch_related("steps__resource_need", "options", "photos__media")
        .order_by("position", "name")
    )


def showcase_queryset() -> QuerySet[ProProfile]:
    """Everything a showcase page shows, in a few queries."""
    return ProProfile.objects.select_related(
        "user",
        "country",
        "photo",
        "cover",
        "bio_voice",
        "itinerary_video",
        "landmarks_voice",
    ).prefetch_related(
        "trades",
        "opening_periods",
        "closures",
        Prefetch("services", queryset=visible_services(), to_attr="visible_services"),
        Prefetch("categories", queryset=ServiceCategory.objects.order_by("position", "name")),
        Prefetch(
            "portfolio",
            queryset=PortfolioItem.objects.select_related("media", "before_media", "service"),
        ),
    )


def card_queryset(queryset: QuerySet[ProProfile]) -> QuerySet[ProProfile]:
    """What a search result card needs."""
    return queryset.select_related("photo", "country", "user").prefetch_related(
        "trades",
        "opening_periods",
        Prefetch("closures", queryset=Closure.objects.all()),
    )


def published_pro(slug: str, *, viewer=None) -> ProProfile | None:
    """A published showcase; its owner also sees it as a draft (preview)."""
    pro = showcase_queryset().filter(slug=slug.lower()).first()
    if pro is None:
        return None
    if pro.is_published or (
        viewer is not None and viewer.is_authenticated and pro.user_id == viewer.pk
    ):
        return pro
    return None


def places() -> list[dict]:
    """Cities and districts where pros are published, the busiest first."""
    rows = (
        ProProfile.objects.filter(status=ProProfile.Status.PUBLISHED)
        .exclude(city="")
        .values("country__code", "city", "district")
        .annotate(pros=Count("pk"))
        .order_by("-pros", "city", "district")
    )
    cities: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (row["country__code"] or "", row["city"])
        city = cities.setdefault(
            key, {"country": key[0], "city": row["city"], "pros": 0, "districts": []}
        )
        city["pros"] += row["pros"]
        if row["district"]:
            city["districts"].append(row["district"])
    return sorted(cities.values(), key=lambda c: -c["pros"])


def opening_periods_of(pro: ProProfile) -> list[OpeningPeriod]:
    return list(pro.opening_periods.all())


def upcoming_closures(pro: ProProfile, today) -> list[Closure]:
    return [c for c in pro.closures.all() if c.ends_on >= today]


def can_collect_payments(pro: ProProfile) -> bool:
    """Without verification a pro can publish but not cash in (setting, per country)."""
    required = get_setting(
        "pros.verification_required_to_collect", country=pro.country, default=True
    )
    return pro.is_verified or not required


def pending_verifications_q() -> Q:
    return Q(verification_status=ProProfile.Verification.PENDING)
