"""The whole world can sign up: every country, its calling code, and a city search."""

import gzip

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.core import geo
from apps.core.models import City, Country, Currency

pytestmark = pytest.mark.django_db


def test_every_country_comes_with_its_calling_code_and_currency():
    created = geo.load_countries()
    assert created["countries"] > 200
    france = Country.objects.get(code="FR")
    assert france.phone_prefix == "+33" and france.timezone == "Europe/Paris"
    japan = Country.objects.get(code="JP")
    assert japan.phone_prefix == "+81"
    assert Currency.objects.get(code="JPY").decimal_places == 0
    again = geo.load_countries()
    assert again == {"countries": 0, "currencies": 0}


def test_a_country_edited_in_the_admin_is_kept():
    geo.load_countries()
    Country.objects.filter(code="FR").update(timezone="Europe/Monaco")
    geo.load_countries()
    assert Country.objects.get(code="FR").timezone == "Europe/Monaco"


def _cities(tmp_path, *rows):
    path = tmp_path / "cities.tsv.gz"
    with gzip.open(path, "wt", encoding="utf-8") as out:
        out.write("".join("\t".join(row) + "\n" for row in rows))
    return path


def test_cities_load_once_and_are_found_without_accents(tmp_path):
    geo.load_countries()
    path = _cities(
        tmp_path,
        ("FR", "Saint-Étienne", "42", "42000", "45.43", "4.39", "170000"),
        ("FR", "Sainte-Foy", "69", "69110", "45.73", "4.8", "20000"),
        ("BJ", "Cotonou", "", "", "6.37", "2.42", "700000"),
        ("ZZ", "Nowhere", "", "", "", "", "1"),
    )
    assert geo.load_cities(path) == 3
    assert geo.load_cities(path) == 0
    assert [c.name for c in geo.search_cities("st etienne")] == ["Saint-Étienne"]
    assert [c.name for c in geo.search_cities("SAINT-E")] == ["Saint-Étienne"]
    assert [c.name for c in geo.search_cities("42000")] == ["Saint-Étienne"]
    assert [c.name for c in geo.search_cities("foy")] == ["Sainte-Foy"]
    assert list(geo.search_cities("c")) == []
    assert [c.name for c in geo.search_cities("coto", country="FR")] == []
    assert City.objects.get(name="Cotonou").location is not None


def test_the_api_searches_cities_for_anyone(tmp_path):
    geo.load_countries()
    geo.load_cities(_cities(tmp_path, ("FR", "Paris", "75", "75001", "48.85", "2.35", "2100000")))
    answer = APIClient().get(reverse("v1:cities"), {"q": "par", "country": "fr"})
    assert answer.status_code == 200
    row = answer.json()[0]
    assert row["name"] == "Paris" and row["country"] == "FR" and row["postal_code"] == "75001"
    assert row["latitude"] == 48.85
    assert APIClient().get(reverse("v1:cities")).status_code == 400


def test_the_real_reference_files_are_readable():
    assert (geo.DATA / "countries.json").exists()
    with gzip.open(geo.DATA / "cities.tsv.gz", "rt", encoding="utf-8") as lines:
        first = next(lines).rstrip("\n").split("\t")
    assert len(first) == 7
