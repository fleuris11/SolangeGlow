import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import GuestIdentity
from apps.accounts.tests.factories import UserFactory
from apps.core.tests.factories import CountryFactory
from apps.notifications.models import Notification
from apps.pros import search
from apps.pros.models import PortfolioItem, ProProfile

from .factories import ProFactory, add_service, open_every_day, picture

pytestmark = pytest.mark.django_db
HEADERS = {"HTTP_X_SG_CLIENT": "web"}


def signed_in(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def pro():
    pro = ProFactory(
        slug="aicha",
        business_name="Aïcha Tresses",
        address="Rue 12.345, maison bleue",
        landmarks="Après la pharmacie, portail bleu",
    )
    add_service(pro)
    open_every_day(pro)
    search.refresh_search(pro)
    return pro


# --- Public showcase -----------------------------------------------------------------------


def test_public_showcase(api_client, pro):
    response = api_client.get(reverse("v1:pro-showcase", args=["AICHA"]))
    assert response.status_code == 200
    data = response.json()
    assert data["business_name"] == "Aïcha Tresses"
    assert data["short_link"].endswith("/aicha")
    assert data["services"][0]["price_minor"] == 15000
    assert data["opening"]["is_open"] is True
    assert data["place"]["address"] == "Rue 12.345, maison bleue"
    assert data["place"]["directions_url"].startswith("https://www.google.com/maps/dir/")
    assert data["trades"][0]["key"] == "braids"


def test_home_visit_pro_keeps_her_address_private(api_client, pro):
    pro.receives_clients = False
    pro.travels_to_clients = True
    pro.service_radius_km = 8
    pro.save()
    place = api_client.get(reverse("v1:pro-showcase", args=["aicha"])).json()["place"]
    assert place["address"] is None and place["latitude"] is None
    assert place["landmarks"] == "" and place["directions_url"] is None


def test_draft_is_hidden_except_for_its_owner(api_client, pro):
    pro.status = ProProfile.Status.DRAFT
    pro.save()
    url = reverse("v1:pro-showcase", args=["aicha"])
    assert api_client.get(url).status_code == 404
    preview = signed_in(pro.user).get(url)
    assert preview.status_code == 200 and preview.json()["status"] == "draft"


def test_expired_session_does_not_block_a_public_page(api_client, pro):
    api_client.cookies["sg_access"] = "not-a-valid-token"
    assert api_client.get(reverse("v1:pro-showcase", args=["aicha"])).status_code == 200


# --- Search, map, places -------------------------------------------------------------------


def test_search_endpoint_with_cursor(api_client, settings):
    for index in range(3):
        search.refresh_search(ProFactory(slug=f"pro-{index}", rating_average=4 + index / 10))
    from apps.core.tests.factories import PlatformSettingFactory

    PlatformSettingFactory(key="search.page_size", value="2")
    first = api_client.get(reverse("v1:pros-search")).json()
    assert [c["slug"] for c in first["results"]] == ["pro-2", "pro-1"]
    assert first["count"] == 3 and first["next"]
    second = api_client.get(reverse("v1:pros-search"), {"cursor": first["next"]}).json()
    assert [c["slug"] for c in second["results"]] == ["pro-0"] and second["next"] is None


def test_search_with_position_returns_distances(api_client, pro):
    response = api_client.get(
        reverse("v1:pros-search"), {"lat": 6.37, "lng": 2.42, "q": "tresses", "open_now": "true"}
    )
    card = response.json()["results"][0]
    assert card["slug"] == "aicha" and 0 < card["distance_m"] < 2000
    assert card["open_now"] is True and card["min_price"] == 15000


def test_map_points_in_a_box(api_client, pro):
    response = api_client.get(reverse("v1:pros-map"), {"bbox": "2.3,6.3,2.5,6.5"})
    data = response.json()
    assert data["type"] == "FeatureCollection" and not data["truncated"]
    assert data["features"][0]["properties"]["slug"] == "aicha"
    assert api_client.get(reverse("v1:pros-map"), {"bbox": "oops"}).status_code == 400


def test_places_and_map_config(api_client, pro):
    places = api_client.get(reverse("v1:pros-places")).json()
    assert places == [{"country": "BJ", "city": "Cotonou", "pros": 1, "districts": ["Fidjrossè"]}]
    config = api_client.get(reverse("v1:map-config"), {"country": "BJ"}).json()
    assert config["style_url"].startswith("https://") and config["attribution"]


# --- QR codes ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "content_type", "magic"),
    [
        ("card.png", "image/png", b"\x89PNG"),
        ("poster.pdf", "application/pdf", b"%PDF"),
        ("stickers.pdf", "application/pdf", b"%PDF"),
    ],
)
def test_printables(api_client, pro, name, content_type, magic):
    url = reverse("v1:pro-printable", args=["aicha", name])
    response = api_client.get(url, {"download": "1"})
    assert response.status_code == 200
    assert response["Content-Type"] == content_type
    assert response.content.startswith(magic)
    assert response["Content-Disposition"].startswith("attachment")


def test_unknown_printable_is_404(api_client, pro):
    url = reverse("v1:pro-printable", args=["aicha", "flyer.doc"])
    assert api_client.get(url).status_code == 404


# --- « I am outside » ----------------------------------------------------------------------


def test_arrival_needs_an_identity_then_notifies(api_client, pro):
    url = reverse("v1:pro-arrival", args=["aicha"])
    refused = api_client.post(url, **HEADERS)
    assert refused.status_code == 401 and refused.json()["code"] == "identity_required"

    guest = GuestIdentity.objects.create(first_name="Bernadette", phone="+2290196000000")
    api_client.cookies["sg_guest"] = str(guest.pk)
    assert api_client.post(url, **HEADERS).json() == {"sent": True}
    assert Notification.objects.filter(user=pro.user, event_key="pros.client_arrived").exists()
    again = api_client.post(url, **HEADERS)
    assert again.status_code == 429 and again.json()["code"] == "arrival_too_soon"


# --- My showcase ---------------------------------------------------------------------------


def test_become_pro_then_edit_and_publish():
    user = UserFactory(country=CountryFactory())
    client = signed_in(user)
    created = client.post(
        reverse("v1:my-pro"),
        {"business_name": "Gloria Make-up", "trades": ["makeup"], "city": "Cotonou"},
        format="json",
        **HEADERS,
    )
    assert created.status_code == 201
    data = created.json()
    assert data["status"] == "draft" and data["slug"] == "gloria-make-up"
    assert set(data["missing"]) == {"location", "services"}

    client.put(
        reverse("v1:my-pro-location"),
        {"latitude": 6.36, "longitude": 2.44, "source": "gps"},
        format="json",
        **HEADERS,
    )
    service = client.post(
        reverse("v1:my-pro-services"),
        {
            "name": "Maquillage mariée",
            "price_kind": "from",
            "price_minor": 25000,
            "steps": [{"kind": "work", "duration_minutes": 90}],
            "options": [{"name": "Essai", "price_minor": 10000}],
        },
        format="json",
        **HEADERS,
    )
    assert service.status_code == 201 and service.json()["duration_minutes"] == 90

    patched = client.patch(
        reverse("v1:my-pro"),
        {"bio": "Maquilleuse depuis 10 ans.", "slug": "gloria", "languages": ["fr", "fon"]},
        format="json",
        **HEADERS,
    )
    assert patched.json()["slug"] == "gloria"

    published = client.post(reverse("v1:my-pro-publication"), **HEADERS)
    assert published.status_code == 200 and published.json()["status"] == "published"
    assert published.json()["missing"] == []


def test_publication_refused_with_the_missing_items():
    pro = ProFactory(status=ProProfile.Status.DRAFT, published_at=None)
    response = signed_in(pro.user).post(reverse("v1:my-pro-publication"), **HEADERS)
    assert response.status_code == 400
    assert response.json()["code"] == "not_ready" and response.json()["missing"] == ["services"]


def test_someone_without_showcase_gets_404():
    response = signed_in(UserFactory()).get(reverse("v1:my-pro"))
    assert response.status_code == 404 and response.json()["code"] == "not_a_pro"


def test_slug_check_suggests_another_link(pro):
    ProFactory(slug="gloria")
    client = signed_in(pro.user)
    free = client.get(reverse("v1:my-pro-slug"), {"slug": "aicha-calavi"}).json()
    assert free["available"] is True
    taken = client.get(reverse("v1:my-pro-slug"), {"slug": "gloria"}).json()
    assert taken["available"] is False and taken["slug"] == "gloria-2"


def test_hours_and_closures(pro):
    client = signed_in(pro.user)
    week = {
        "periods": [
            {"weekday": 0, "opens_at": "09:00", "closes_at": "12:00"},
            {"weekday": 0, "opens_at": "14:00", "closes_at": "19:00"},
        ]
    }
    saved = client.put(reverse("v1:my-pro-hours"), week, format="json", **HEADERS)
    assert saved.status_code == 200 and len(saved.json()["periods"]) == 2
    overlap = {"periods": [{"weekday": 1, "opens_at": "10:00", "closes_at": "09:00"}]}
    refused = client.put(reverse("v1:my-pro-hours"), overlap, format="json", **HEADERS)
    assert refused.status_code == 400

    closure = client.post(
        reverse("v1:my-pro-closures"),
        {"starts_on": "2026-12-24", "ends_on": "2026-12-26", "reason": "Noël"},
        format="json",
        **HEADERS,
    )
    assert closure.status_code == 201
    removed = client.delete(reverse("v1:my-pro-closure", args=[closure.json()["id"]]), **HEADERS)
    assert removed.status_code == 204


def test_portfolio_upload_update_and_delete(pro):
    client = signed_in(pro.user)
    service = pro.services.get()
    created = client.post(
        reverse("v1:my-pro-portfolio"),
        {"file": picture("after.png"), "before": picture("before.png"), "caption": "Knotless",
         "service_id": str(service.pk)},
        format="multipart",
        **HEADERS,
    )  # fmt: skip
    assert created.status_code == 202
    item_id = created.json()["id"]
    assert created.json()["service_name"] == service.name
    assert created.json()["before"] is not None

    updated = client.patch(
        reverse("v1:my-pro-portfolio-item", args=[item_id]),
        {"caption": "Knotless mi-dos"},
        format="json",
        **HEADERS,
    )
    assert updated.json()["caption"] == "Knotless mi-dos"
    client.delete(reverse("v1:my-pro-portfolio-item", args=[item_id]), **HEADERS)
    assert not PortfolioItem.objects.exists()


def test_showcase_media_upload(pro):
    client = signed_in(pro.user)
    response = client.post(
        reverse("v1:my-pro-media", args=["photo"]),
        {"file": picture()},
        format="multipart",
        **HEADERS,
    )
    assert response.status_code == 202
    assert response.json()["photo"]["status"] == "ready"  # Celery runs eagerly in tests
    unknown = client.post(
        reverse("v1:my-pro-media", args=["avatar"]),
        {"file": picture()},
        format="multipart",
        **HEADERS,
    )
    assert unknown.status_code == 404


def test_another_pro_cannot_touch_my_services(pro):
    intruder = ProFactory(slug="intruder")
    service = pro.services.get()
    response = signed_in(intruder.user).patch(
        reverse("v1:my-pro-service", args=[service.pk]),
        {"name": "Hacked"},
        format="json",
        **HEADERS,
    )
    assert response.status_code == 404


def test_verification_upload(pro):
    client = signed_in(pro.user)
    response = client.post(
        reverse("v1:my-pro-verification"),
        {"document_type": "id_card", "document": picture("id.png"), "selfie": picture("me.png")},
        format="multipart",
        **HEADERS,
    )
    assert response.status_code == 202
    assert response.json()["status"] == "pending"
    assert response.json()["can_collect_payments"] is False
