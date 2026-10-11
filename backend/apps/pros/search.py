"""Finding pros: words (full text + trigrams), trade, place, distance, price, rating, hours.

Words are compared without accents and in lowercase, so "tresse a calavi" finds
"Tresses" in "Abomey-Calavi". Trade names are indexed in every language.
"""

from __future__ import annotations

import base64
import re
import unicodedata
from dataclasses import dataclass

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point, Polygon
from django.contrib.gis.measure import D
from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
    TrigramWordSimilarity,
)
from django.db.models import (
    ExpressionWrapper,
    F,
    FloatField,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Value,
)
from django.db.models.functions import Coalesce

from apps.core.selectors import get_setting

from .hours import open_now_q
from .models import ProProfile, Service, SpokenLanguage

# Small words of a spoken or typed query that do not help ("tresses à Calavi").
STOP_WORDS = {
    "a", "au", "aux", "chez", "de", "des", "du", "en", "et", "la", "le", "les", "l", "d",
    "pour", "pres", "sur", "une", "un", "the", "in", "at", "near", "for", "of", "and", "me",
    "moi", "je", "cherche", "veux", "v", "na", "pri",
}  # fmt: skip
TRIGRAM_THRESHOLD = 0.45


def normalize(text: str) -> str:
    """Lowercase, no accents, words separated by single spaces."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s-]", " ", plain.lower())).strip()


def query_words(text: str) -> list[str]:
    words = re.split(r"[\s-]+", normalize(text))
    return [w for w in words if len(w) > 1 and w not in STOP_WORDS][:8]


def build_document(pro: ProProfile) -> str:
    parts = [pro.business_name, pro.user.first_name, pro.city, pro.district, pro.bio[:300]]
    for trade in pro.trades.all():
        parts += [trade.key, trade.name_fr, trade.name_en, trade.name_sk]
    services = pro.services.filter(is_active=True, archived_at__isnull=True)
    parts += list(services.values_list("name", flat=True))
    parts += list(pro.categories.values_list("name", flat=True))
    labels = dict(SpokenLanguage.choices)
    parts += [str(labels.get(code, "")) for code in pro.languages]
    if pro.travels_to_clients:
        parts += ["domicile", "home", "domov"]
    return normalize(" ".join(p or "" for p in parts))


def refresh_search(pro: ProProfile) -> None:
    pro.search_document = build_document(pro)
    ProProfile.objects.filter(pk=pro.pk).update(search_document=pro.search_document)
    ProProfile.objects.filter(pk=pro.pk).update(
        search_vector=SearchVector("search_document", config="simple")
    )


@dataclass
class SearchParams:
    q: str = ""
    trade: str = ""
    city: str = ""
    district: str = ""
    near: Point | None = None
    radius_km: float | None = None
    price_max: int | None = None
    currency: str = ""
    rating_min: float | None = None
    open_now: bool = False
    at_home: bool = False
    verified: bool = False
    bbox: tuple[float, float, float, float] | None = None
    sort: str = ""


def _min_price():
    services = Service.objects.filter(
        pro=OuterRef("pk"), is_active=True, archived_at__isnull=True, price_minor__isnull=False
    ).exclude(price_kind=Service.PriceKind.QUOTE)
    return Subquery(services.order_by("price_minor").values("price_minor")[:1])


def search(params: SearchParams) -> QuerySet[ProProfile]:
    pros = ProProfile.objects.filter(status=ProProfile.Status.PUBLISHED).annotate(
        min_price=_min_price()
    )

    if params.trade:
        pros = pros.filter(trades__key=params.trade, trades__is_active=True)
    if params.city:
        pros = pros.filter(city__iexact=params.city.strip())
    if params.district:
        pros = pros.filter(district__iexact=params.district.strip())
    if params.rating_min is not None:
        pros = pros.filter(rating_average__gte=params.rating_min)
    if params.verified:
        pros = pros.filter(verification_status=ProProfile.Verification.VERIFIED)
    if params.price_max is not None:
        pros = pros.filter(min_price__lte=params.price_max)
        if params.currency:
            pros = pros.filter(currency=params.currency.upper())
    if params.open_now:
        pros = pros.filter(open_now_q())
    if params.bbox:
        pros = pros.filter(
            location__intersects=Polygon.from_bbox(params.bbox), receives_clients=True
        )

    if params.near is not None:
        pros = pros.annotate(distance=Distance("location", params.near))
        if params.at_home:
            pros = pros.filter(travels_to_clients=True).filter(
                Q(service_area__intersects=params.near)
                | Q(service_area__isnull=True, distance__lte=F("service_radius_km") * 1000.0)
            )
        else:
            default = float(get_setting("search.default_radius_km", default=10))
            maximum = float(get_setting("search.max_radius_km", default=50))
            radius = min(params.radius_km or default, maximum)
            pros = pros.filter(location__dwithin=(params.near, D(km=radius)))
    elif params.at_home:
        pros = pros.filter(travels_to_clients=True)

    words = query_words(params.q)
    if words:
        query = SearchQuery(" & ".join(f"{w}:*" for w in words), search_type="raw", config="simple")
        pros = pros.annotate(rank=SearchRank(F("search_vector"), query))
        exact = pros.filter(search_vector=query)
        if exact.exists():  # every word found
            pros = exact.annotate(similarity=Value(1.0, output_field=FloatField()))
        else:  # forgive typos: each word must look like a word of the showcase
            similarities = {
                f"sim_{index}": TrigramWordSimilarity(word, "search_document")
                for index, word in enumerate(words)
            }
            pros = pros.annotate(**similarities).filter(
                **{f"{name}__gte": TRIGRAM_THRESHOLD for name in similarities}
            )
            total = sum((F(name) for name in similarities), Value(0.0))
            pros = pros.annotate(similarity=ExpressionWrapper(total, output_field=FloatField()))

    return pros.order_by(*_ordering(params, bool(words)))


def _ordering(params: SearchParams, has_words: bool) -> list:
    rating = Coalesce("rating_average", Value(0), output_field=FloatField()).desc()
    if params.sort == "rating":
        return [rating, "-rating_count", "pk"]
    if params.sort == "price":
        return [F("min_price").asc(nulls_last=True), "pk"]
    if params.sort == "distance" and params.near is not None:
        return ["distance", "pk"]
    if has_words:
        return [F("rank").desc(), F("similarity").desc(), rating, "pk"]
    if params.near is not None:
        return ["distance", "pk"]
    return [rating, "-published_at", "pk"]


# --- Cursor: an opaque position in the results ------------------------------------


def encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(f"o:{offset}".encode()).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        return max(0, int(raw.removeprefix("o:")))
    except (ValueError, UnicodeDecodeError):
        return 0
