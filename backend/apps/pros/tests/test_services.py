import datetime
from zoneinfo import ZoneInfo

import pytest
from django.contrib.gis.geos import Point

from apps.accounts.tests.factories import UserFactory
from apps.core.audit.models import AuditEvent
from apps.core.choices import Role
from apps.core.tests.factories import CountryFactory, PlatformSettingFactory
from apps.notifications.models import Notification
from apps.pros import errors, hours, selectors, services, vault
from apps.pros.models import ProProfile, ProVerification, Service

from .factories import ProFactory, add_service, open_every_day, picture

pytestmark = pytest.mark.django_db


def setting(key, value, value_type="integer", country=None):
    return PlatformSettingFactory(key=key, value=value, value_type=value_type, country=country)


# --- Becoming a pro, profile ----------------------------------------------------------


def test_become_pro_creates_a_draft_with_a_short_link():
    benin = CountryFactory()
    user = UserFactory(first_name="Aïcha", country=benin)

    pro = services.become_pro(
        user, business_name="Aïcha Tresses", trade_keys=["braids", "nope"], city="Cotonou"
    )

    assert pro.status == ProProfile.Status.DRAFT
    assert pro.slug == "aicha-tresses"
    assert pro.currency == "XOF"
    assert [t.key for t in pro.trades.all()] == ["braids"]
    assert Role.PRO in user.roles
    assert "tresses" in pro.search_document and "aicha" in pro.search_document


def test_suggested_link_avoids_taken_and_reserved_words():
    ProFactory(slug="aicha")
    assert services.suggest_slug("Aïcha") == "aicha-2"
    assert services.suggest_slug("Me") == "me-pro"


@pytest.mark.parametrize("slug", ["ab", "-aicha", "aicha-", "a--b", "Aïcha!", "explore", "api"])
def test_invalid_or_reserved_links_are_refused(slug):
    with pytest.raises(errors.SlugInvalid):
        services.check_slug(slug)


def test_a_link_already_used_is_refused():
    ProFactory(slug="gloria")
    with pytest.raises(errors.SlugTaken):
        services.check_slug("gloria")


def test_update_profile_cleans_social_links_and_languages():
    pro = ProFactory()
    services.update_profile(
        pro,
        actor=pro.user,
        social_links={
            "instagram": "aicha.tresses",
            "whatsapp": "+229 01 97 12 34 56",
            "tiktok": "",
        },
        languages=["fr", "fon", "fr", "xx"],
        slug="aicha-tresses",
    )
    pro.refresh_from_db()
    assert pro.social_links == {"instagram": "@aicha.tresses", "whatsapp": "+2290197123456"}
    assert pro.languages == ["fr", "fon"]
    assert pro.slug == "aicha-tresses"
    assert AuditEvent.objects.filter(action="pros.updated").exists()


@pytest.mark.parametrize(
    "links",
    [{"instagram": "javascript:alert(1)"}, {"website": "not a site"}, {"myspace": "x"}],
)
def test_bad_social_links_are_refused(links):
    pro = ProFactory()
    with pytest.raises(errors.InvalidSocialLink):
        services.update_profile(pro, actor=pro.user, social_links=links)


# --- Place and home visits -------------------------------------------------------------


def test_location_is_set_and_journaled():
    pro = ProFactory(location=None)
    services.set_location(pro, latitude=6.37, longitude=2.39, source="gps", actor=pro.user)
    pro.refresh_from_db()
    assert (round(pro.location.y, 2), round(pro.location.x, 2)) == (6.37, 2.39)
    assert pro.location_source == "gps"
    assert AuditEvent.objects.filter(action="pros.location_changed").exists()


def test_travel_radius_is_limited_by_a_setting():
    setting("pros.service_area_max_radius_km", "15")
    pro = ProFactory()
    with pytest.raises(errors.RadiusTooLarge):
        services.set_travel(pro, travels=True, radius_km=20, actor=pro.user)
    services.set_travel(pro, travels=True, radius_km=12, fee_minor=2000, actor=pro.user)
    pro.refresh_from_db()
    assert (pro.service_radius_km, pro.travel_fee_minor) == (12, 2000)


def test_travel_area_drawn_on_the_map():
    pro = ProFactory()
    area = [[2.38, 6.35], [2.45, 6.35], [2.45, 6.40], [2.38, 6.40]]
    services.set_travel(pro, travels=True, area=area, actor=pro.user)
    pro.refresh_from_db()
    assert pro.service_area.contains(Point(2.42, 6.37, srid=4326))
    assert pro.service_radius_km is None
    with pytest.raises(errors.InvalidArea):
        services.set_travel(pro, travels=True, area=[[2.38, 6.35], [2.45, 6.35]], actor=pro.user)


# --- Publication ---------------------------------------------------------------------------


def test_publication_lists_what_is_missing_then_publishes():
    pro = ProFactory(status=ProProfile.Status.DRAFT, published_at=None, location=None)
    with pytest.raises(errors.NotReadyToPublish) as refused:
        services.publish(pro, actor=pro.user)
    assert refused.value.details["missing"] == ["location", "services"]

    pro.location = Point(2.41, 6.36, srid=4326)
    pro.save()
    add_service(pro)
    services.publish(pro, actor=pro.user)

    assert pro.status == ProProfile.Status.PUBLISHED
    assert Notification.objects.filter(user=pro.user, event_key="pros.published").exists()


def test_suspended_showcase_cannot_be_published_and_comes_back_after():
    owner = UserFactory(email="team@example.com")
    pro = ProFactory()
    services.suspend(pro, actor=owner, reason="Fausses photos")
    with pytest.raises(errors.Suspended):
        services.publish(pro, actor=pro.user)
    assert Notification.objects.filter(user=pro.user, event_key="pros.suspended").exists()

    services.reinstate(pro, actor=owner)
    assert pro.status == ProProfile.Status.PUBLISHED
    actions = set(AuditEvent.objects.values_list("action", flat=True))
    assert {"pros.suspended", "pros.reinstated"} <= actions


# --- Services (price list) ---------------------------------------------------------------


def test_service_with_waiting_time_and_options():
    pro = ProFactory()
    service = services.save_service(
        pro,
        {
            "name": "Coloration",
            "price_kind": "from",
            "price_minor": 12000,
            "steps": [
                {"kind": "work", "duration_minutes": 30},
                {"kind": "wait", "label": "Pose", "duration_minutes": 40},
                {"kind": "work", "duration_minutes": 20},
            ],
            "options": [{"name": "Mèches fournies", "price_minor": 5000, "extra_minutes": 15}],
        },
    )
    assert service.duration_minutes == 90
    assert (service.work_minutes, service.waiting_minutes) == (50, 40)
    assert [s.needs_staff for s in service.steps.all()] == [True, False, True]
    assert service.options.get().price_minor == 5000
    assert service.currency == "XOF"


def test_quote_has_no_price_and_a_price_is_required_otherwise():
    pro = ProFactory()
    quote = services.save_service(
        pro,
        {"name": "Robe de mariée", "price_kind": "quote", "price_minor": 999,
         "steps": [{"duration_minutes": 60}]},
    )  # fmt: skip
    assert quote.price_minor is None
    with pytest.raises(errors.InvalidPrice):
        services.save_service(
            pro, {"name": "Tresses", "price_kind": "fixed", "steps": [{"duration_minutes": 60}]}
        )
    with pytest.raises(errors.InvalidDuration):
        services.save_service(pro, {"name": "Tresses", "price_kind": "fixed", "price_minor": 1})


def test_number_of_services_is_limited():
    setting("pros.max_services", "1")
    pro = ProFactory()
    add_service(pro)
    with pytest.raises(errors.TooMany):
        services.save_service(
            pro, {"name": "B", "price_kind": "quote", "steps": [{"duration_minutes": 10}]}
        )


def test_archived_service_is_hidden():
    pro = ProFactory()
    service = add_service(pro)
    services.archive_service(service)
    assert not selectors.visible_services().filter(pk=service.pk).exists()
    assert Service.objects.filter(pk=service.pk).exists()  # kept for bookings history


# --- Hours ---------------------------------------------------------------------------------


def test_overlapping_hours_are_refused():
    pro = ProFactory()
    with pytest.raises(errors.InvalidHours):
        services.set_opening_hours(
            pro,
            [
                {"weekday": 0, "opens_at": datetime.time(9), "closes_at": datetime.time(13)},
                {"weekday": 0, "opens_at": datetime.time(12), "closes_at": datetime.time(18)},
            ],
        )


def _at(pro, day, hour, minute=0):
    zone = ZoneInfo(pro.country.timezone)
    return datetime.datetime(2026, 10, day, hour, minute, tzinfo=zone)


def test_open_now_with_a_break_and_next_opening():
    pro = ProFactory()
    # 2026-10-12 is a Monday.
    services.set_opening_hours(
        pro,
        [
            {"weekday": 0, "opens_at": datetime.time(9), "closes_at": datetime.time(12)},
            {"weekday": 0, "opens_at": datetime.time(14), "closes_at": datetime.time(19)},
        ],
    )
    pro = selectors.showcase_queryset().get(pk=pro.pk)

    morning = hours.opening_status(pro, _at(pro, 12, 10))
    assert morning.is_open and morning.closes_at.hour == 12

    lunch = hours.opening_status(pro, _at(pro, 12, 13))
    assert not lunch.is_open and lunch.next_opening.hour == 14

    tuesday = hours.opening_status(pro, _at(pro, 13, 10))
    assert not tuesday.is_open and tuesday.next_opening.day == 19  # next Monday


def test_time_zone_of_the_country_is_used():
    paris = CountryFactory(code="FR", name="France", timezone="Europe/Paris")
    pro = ProFactory(country=paris)
    services.set_opening_hours(
        pro, [{"weekday": 0, "opens_at": datetime.time(9), "closes_at": datetime.time(10)}]
    )
    pro = selectors.showcase_queryset().get(pk=pro.pk)
    # 07:30 UTC = 09:30 in Paris (summer time).
    moment = datetime.datetime(2026, 10, 12, 7, 30, tzinfo=datetime.UTC)
    assert hours.opening_status(pro, moment).is_open
    assert ProProfile.objects.filter(hours.open_now_q(moment), pk=pro.pk).exists()


def test_exceptional_closure_wins_over_hours():
    pro = ProFactory()
    open_every_day(pro)
    services.add_closure(
        pro, starts_on=datetime.date(2026, 10, 12), ends_on=datetime.date(2026, 10, 14)
    )
    pro = selectors.showcase_queryset().get(pk=pro.pk)
    status = hours.opening_status(pro, _at(pro, 13, 12))
    assert not status.is_open and status.closed_today
    assert status.next_opening.day == 15
    assert not ProProfile.objects.filter(hours.open_now_q(_at(pro, 13, 12)), pk=pro.pk).exists()
    with pytest.raises(errors.InvalidClosure):
        services.add_closure(
            pro, starts_on=datetime.date(2026, 10, 14), ends_on=datetime.date(2026, 10, 12)
        )


# --- Portfolio -----------------------------------------------------------------------------


def test_portfolio_before_after_linked_to_a_service():
    pro = ProFactory()
    service = add_service(pro)
    item = services.add_portfolio_item(
        pro, uploaded=picture("after.png"), before=picture("before.png"), service=service
    )
    assert item.media.purpose == "portfolio" and item.before_media is not None
    assert item.service == service
    setting("pros.max_portfolio_items", "1")
    with pytest.raises(errors.TooMany):
        services.add_portfolio_item(pro, uploaded=picture())


# --- Verification ------------------------------------------------------------------------


def test_identity_documents_are_encrypted_and_each_reading_is_journaled():
    pro = ProFactory()
    team = UserFactory(email="verif@example.com")
    verification = services.submit_verification(
        pro,
        document=picture("id.jpg", fmt="JPEG"),
        selfie=picture("me.png"),
        document_type="passport",
    )
    with verification.document_file.open("rb") as handle:
        stored = handle.read()
    assert not stored.startswith(b"\xff\xd8")  # not a readable JPEG
    assert vault.open_sealed(verification.document_file).startswith(b"\xff\xd8")
    pro.refresh_from_db()
    assert pro.verification_status == ProProfile.Verification.PENDING

    with pytest.raises(errors.VerificationAlreadySent):
        services.submit_verification(
            pro, document=picture(), selfie=picture(), document_type="id_card"
        )

    services.read_verification_file(verification, "selfie", actor=team)
    event = AuditEvent.objects.get(action="pros.identity_viewed")
    assert event.actor == team and event.metadata == {"file": "selfie"}


def test_review_verification_gives_the_badge_or_the_reason():
    team = UserFactory(email="verif@example.com")
    pro = ProFactory()
    first = services.submit_verification(
        pro, document=picture(), selfie=picture(), document_type="id_card"
    )
    services.review_verification(first, actor=team, approve=False, reason="Photo floue")
    pro.refresh_from_db()
    assert pro.verification_status == ProProfile.Verification.REJECTED
    rejected = Notification.objects.get(event_key="pros.verification_rejected")
    assert "Photo floue" in rejected.body

    second = services.submit_verification(
        pro, document=picture(), selfie=picture(), document_type="id_card"
    )
    services.review_verification(second, actor=team, approve=True)
    pro.refresh_from_db()
    assert pro.is_verified and pro.verified_at is not None
    assert second.status == ProVerification.Status.APPROVED
    with pytest.raises(errors.AlreadyVerified):
        services.submit_verification(
            pro, document=picture(), selfie=picture(), document_type="id_card"
        )


def test_an_unreadable_document_is_refused():
    from django.core.files.uploadedfile import SimpleUploadedFile

    pro = ProFactory()
    fake = SimpleUploadedFile("id.jpg", b"not a picture", content_type="image/jpeg")
    with pytest.raises(errors.MediaNotReady):
        services.submit_verification(pro, document=fake, selfie=picture(), document_type="id_card")


def test_cashing_in_needs_verification_unless_the_setting_says_otherwise():
    pro = ProFactory()
    assert not selectors.can_collect_payments(pro)
    setting("pros.verification_required_to_collect", "false", value_type="boolean")
    assert selectors.can_collect_payments(pro)


# --- « I am outside » -----------------------------------------------------------------------


def test_arrival_notifies_the_pro_once_per_cooldown():
    pro = ProFactory()
    client = UserFactory(email="awa@example.com", first_name="Awa")
    services.announce_arrival(pro, user=client)
    alert = Notification.objects.get(user=pro.user, event_key="pros.client_arrived")
    assert alert.title.startswith("Awa")
    with pytest.raises(errors.ArrivalTooSoon):
        services.announce_arrival(pro, user=client)


def test_arrival_is_refused_for_home_visit_only_pros():
    pro = ProFactory(receives_clients=False, travels_to_clients=True, service_radius_km=5)
    with pytest.raises(errors.ArrivalNotPossible):
        services.announce_arrival(pro, guest_name="Bernadette", guest_key="g1")
