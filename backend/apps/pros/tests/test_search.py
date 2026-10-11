import datetime

import pytest
from django.contrib.gis.geos import Point, Polygon
from django.utils import timezone

from apps.pros import search, services
from apps.pros.models import ProProfile
from apps.pros.serializers import card_payload

from .factories import ProFactory, add_service, open_every_day

pytestmark = pytest.mark.django_db

CALAVI = Point(2.3417, 6.4485, srid=4326)
AKPAKPA = Point(2.4469, 6.3561, srid=4326)
PARIS = Point(2.3522, 48.8566, srid=4326)


def indexed(**kwargs) -> ProProfile:
    pro = ProFactory(**kwargs)
    search.refresh_search(pro)
    return pro


def slugs(params: search.SearchParams) -> list[str]:
    return [pro.slug for pro in search.search(params)]


def test_words_without_accents_trades_and_places():
    aicha = indexed(
        slug="aicha", business_name="Chez Aïcha", city="Abomey-Calavi", trades=["braids"]
    )
    indexed(
        slug="gloria",
        business_name="Gloria Make-up",
        city="Cotonou",
        trades=["makeup"],
        user__first_name="Gloria",
    )

    assert slugs(search.SearchParams(q="tresses à Calavi")) == ["aicha"]
    assert slugs(search.SearchParams(q="aicha")) == ["aicha"]
    assert slugs(search.SearchParams(q="braids")) == ["aicha"]  # English trade name
    assert slugs(search.SearchParams(q="maquillage")) == ["gloria"]
    assert aicha.search_document == search.build_document(aicha)


def test_typos_are_forgiven():
    indexed(slug="gloria", business_name="Gloria Beauté", trades=["makeup"])
    assert slugs(search.SearchParams(q="beaute glorya")) == ["gloria"]


def test_service_names_are_searchable():
    pro = indexed(slug="senami", trades=["hair"])
    add_service(pro, name="Défrisage")
    search.refresh_search(pro)
    assert slugs(search.SearchParams(q="defrisage")) == ["senami"]


def test_drafts_and_suspended_showcases_are_never_found():
    indexed(slug="draft", status=ProProfile.Status.DRAFT)
    indexed(slug="suspended", status=ProProfile.Status.SUSPENDED)
    indexed(slug="online")
    assert slugs(search.SearchParams()) == ["online"]


def test_trade_city_district_rating_and_verified_filters():
    indexed(slug="a", trades=["braids"], city="Cotonou", district="Akpakpa", rating_average=4.8)
    indexed(slug="b", trades=["nails"], city="Cotonou", district="Fidjrossè", rating_average=4.1,
            verification_status=ProProfile.Verification.VERIFIED)  # fmt: skip
    indexed(slug="c", trades=["braids"], city="Paris", country__code="FR")

    assert slugs(search.SearchParams(trade="braids")) == ["a", "c"]
    assert slugs(search.SearchParams(city="cotonou", district="akpakpa")) == ["a"]
    assert slugs(search.SearchParams(rating_min=4.5)) == ["a"]
    assert slugs(search.SearchParams(verified=True)) == ["b"]


def test_distance_radius_and_sorting():
    indexed(slug="calavi", location=CALAVI)
    indexed(slug="akpakpa", location=AKPAKPA)
    indexed(slug="paris", location=PARIS)
    near_akpakpa = Point(2.44, 6.36, srid=4326)

    assert slugs(search.SearchParams(near=near_akpakpa, radius_km=20)) == ["akpakpa", "calavi"]
    assert slugs(search.SearchParams(near=near_akpakpa, radius_km=3)) == ["akpakpa"]


def test_price_filter_uses_the_cheapest_service_and_ignores_quotes():
    cheap = indexed(slug="cheap")
    add_service(cheap, price=5000)
    add_service(cheap, price=30000, name="Long")
    expensive = indexed(slug="expensive")
    add_service(expensive, price=25000)
    quote = indexed(slug="quote")
    add_service(quote, kind="quote")

    assert slugs(search.SearchParams(price_max=10000)) == ["cheap"]
    assert slugs(search.SearchParams(sort="price"))[:2] == ["cheap", "expensive"]


def test_open_now_filter():
    open_pro = indexed(slug="open")
    open_every_day(open_pro)
    indexed(slug="closed")
    assert slugs(search.SearchParams(open_now=True)) == ["open"]


def test_home_visits_by_radius_or_drawn_area():
    by_radius = indexed(slug="radius", location=AKPAKPA, travels_to_clients=True)
    by_radius.service_radius_km = 5
    by_radius.save()
    area = Polygon.from_bbox((2.30, 6.40, 2.38, 6.50))
    area.srid = 4326
    indexed(slug="area", location=AKPAKPA, travels_to_clients=True, service_area=area)
    indexed(slug="salon-only", location=AKPAKPA)

    client_in_akpakpa = Point(2.45, 6.36, srid=4326)
    client_in_calavi = Point(2.34, 6.45, srid=4326)
    assert slugs(search.SearchParams(near=client_in_akpakpa, at_home=True)) == ["radius"]
    assert slugs(search.SearchParams(near=client_in_calavi, at_home=True)) == ["area"]
    assert sorted(slugs(search.SearchParams(at_home=True))) == ["area", "radius"]


def test_map_box_never_shows_private_addresses():
    indexed(slug="salon", location=AKPAKPA)
    indexed(slug="home", location=AKPAKPA, receives_clients=False, travels_to_clients=True)
    assert slugs(search.SearchParams(bbox=(2.3, 6.3, 2.5, 6.5))) == ["salon"]


def test_card_hides_the_exact_distance_of_a_private_address():
    indexed(slug="home", location=AKPAKPA, receives_clients=False, travels_to_clients=True,
            service_radius_km=10)  # fmt: skip
    near = Point(2.4475, 6.3565, srid=4326)  # about 80 m away
    pro = search.search(search.SearchParams(near=near)).get()
    card = card_payload(pro)
    assert card["distance_m"] == 1000
    assert card["latitude"] is None and card["longitude"] is None


def test_cursor_round_trip():
    assert search.decode_cursor(search.encode_cursor(40)) == 40
    assert search.decode_cursor("garbage!") == 0
    assert search.decode_cursor(None) == 0


def test_published_recently_comes_after_better_rated():
    indexed(slug="new", rating_average=None, published_at=timezone.now())
    indexed(slug="star", rating_average=4.9,
            published_at=timezone.now() - datetime.timedelta(days=30))  # fmt: skip
    assert slugs(search.SearchParams()) == ["star", "new"]


def test_spoken_languages_are_searchable():
    pro = indexed(slug="fon")
    services.update_profile(pro, actor=pro.user, languages=["fon"])
    assert slugs(search.SearchParams(q="fon")) == ["fon"]


def test_demo_showcases_are_complete_and_seeded_once():
    from django.core.management import call_command

    call_command("seed_demo", "--force", verbosity=0)
    call_command("seed_demo", "--force", verbosity=0)
    published = ProProfile.objects.filter(status=ProProfile.Status.PUBLISHED)
    assert published.count() == 30
    assert not published.filter(location__isnull=True).exists()
    assert set(published.values_list("city", flat=True)) >= {
        "Cotonou", "Abomey-Calavi", "Porto-Novo", "Paris", "Brest",
    }  # fmt: skip
    assert all(pro.services.exists() and pro.opening_periods.exists() for pro in published)
    assert slugs(search.SearchParams(q="tresses calavi")) == ["fifonsi", "senami"]
