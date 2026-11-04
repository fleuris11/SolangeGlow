"""Countries and cities of the whole world, from reference files (see data/SOURCES.md)."""

from __future__ import annotations

import gzip
import json
import unicodedata
from pathlib import Path

from django.contrib.gis.geos import Point
from django.db.models import Q

from .models import City, Country, Currency

DATA = Path(__file__).parent / "data"
BATCH = 2000


def normalize(text: str) -> str:
    """Saint-Étienne, saint etienne and ST ETIENNE are the same search."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    words = "".join(c if c.isalnum() else " " for c in plain).split()
    return " ".join("saint" if word == "st" else word for word in words)


def load_countries(path: Path = DATA / "countries.json") -> dict:
    """Adds what is missing: a country or a currency edited in the admin is never overwritten."""
    created = {"countries": 0, "currencies": 0}
    for row in json.loads(path.read_text(encoding="utf-8")):
        currency, new_currency = Currency.objects.get_or_create(
            code=row["currency"],
            defaults={
                "name": row["currency_name"],
                "name_fr": row["currency_name"],
                "name_en": row["currency_name"],
                "name_sk": row["currency_name"],
                "symbol": row["symbol"],
                "decimal_places": row["decimals"],
            },
        )
        created["currencies"] += new_currency
        _, new_country = Country.objects.get_or_create(
            code=row["code"],
            defaults={
                "name": row["name_fr"],
                "name_fr": row["name_fr"],
                "name_en": row["name_en"],
                "name_sk": row["name_sk"],
                "phone_prefix": row["phone_prefix"],
                "default_currency": currency,
                "default_language": row["default_language"],
                "timezone": row["timezone"],
            },
        )
        created["countries"] += new_country
    return created


def load_cities(path: Path = DATA / "cities.tsv.gz") -> int:
    """Once: a database that already has cities keeps them."""
    if City.objects.exists():
        return 0
    countries = dict(Country.objects.values_list("code", "pk"))
    batch: list[City] = []
    total = 0
    with gzip.open(path, "rt", encoding="utf-8") as lines:
        for line in lines:
            code, name, region, postal, lat, lng, population = line.rstrip("\n").split("\t")
            if code not in countries:
                continue
            batch.append(
                City(
                    country_id=countries[code],
                    name=name[:120],
                    search=normalize(name)[:120],
                    region=region[:40],
                    postal_code=postal[:10],
                    location=Point(float(lng), float(lat), srid=4326) if lat and lng else None,
                    population=int(population),
                )
            )
            if len(batch) >= BATCH:
                City.objects.bulk_create(batch)
                total += len(batch)
                batch = []
    City.objects.bulk_create(batch)
    return total + len(batch)


def search_cities(query: str, *, country: str = "", limit: int = 10):
    """By name from its first letters, or by postal code: the biggest come first."""
    text = normalize(query)
    if len(text) < 2:
        return City.objects.none()
    matches = Q(search__startswith=text) | Q(search__contains=f" {text}")
    if text.isdigit():
        matches = Q(postal_code__startswith=text)
    rows = City.objects.filter(matches).select_related("country")
    if country:
        rows = rows.filter(country__code=country.upper())
    return rows.order_by("-population", "name")[:limit]
