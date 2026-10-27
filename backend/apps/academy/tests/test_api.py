"""Academy API: catalogue, course page, getting a course, player, quiz, my courses,
certificate check, pass, lives, trainer space; admin pages and the review queue."""

import datetime

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.academy.models import Certificate, Course, LiveSession
from apps.accounts.tests.factories import UserFactory
from apps.messaging.tests.factories import adult
from apps.pros.models import ProProfile

from .factories import course, setting, trainer, video

pytestmark = pytest.mark.django_db
H = {"HTTP_X_SG_CLIENT": "web"}


def signed_in(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_catalogue_course_page_and_getting_a_free_course():
    pro = trainer()
    shown = course(pro, modules=(("A", 2),), quiz=1)
    course(pro, status=Course.Status.IN_REVIEW)
    anonymous = APIClient()
    page = anonymous.get(reverse("v1:academy-catalogue"), {"country": "BJ"}).json()
    assert [c["slug"] for c in page["results"]] == [shown.slug]
    assert page["results"][0]["lessons_count"] == 2 and page["open"] is True
    assert page["results"][0]["trainer"]["name"] == pro.display_name
    found = anonymous.get(reverse("v1:academy-catalogue"), {"q": "mariée"}).json()
    assert len(found["results"]) == 1

    detail = anonymous.get(reverse("v1:academy-course", args=[shown.slug])).json()
    assert detail["enrollment"] is None and detail["modules"][0]["questions_count"] == 1
    assert detail["modules"][0]["lessons"][0]["is_preview"] is True
    hidden = Course.objects.exclude(pk=shown.pk).get()
    assert anonymous.get(reverse("v1:academy-course", args=[hidden.slug])).status_code == 404

    student = signed_in(adult("Awa"))
    got = student.post(reverse("v1:academy-get", args=[shown.slug]), {}, format="json", **H)
    assert got.status_code == 200 and got.json()["enrollment"]["status"] == "active"
    again = student.post(reverse("v1:academy-get", args=[shown.slug]), {}, format="json", **H)
    assert again.json()["code"] == "already_enrolled"


def test_a_paid_course_answers_with_the_payment_page():
    paid = course(trainer(), pricing=Course.Pricing.PAID, price=5000)
    student = signed_in(adult("Awa"))
    url = reverse("v1:academy-get", args=[paid.slug])
    refused = student.post(url, {}, format="json", **H)
    assert refused.json()["code"] == "waiver_required"
    answer = student.post(
        url, {"waiver": True, "waiver_text": "Je renonce."}, format="json", **H
    ).json()
    assert answer["checkout_url"] and answer["enrollment"] is None


def test_player_position_quiz_my_courses_and_certificate():
    student_user = adult("Awa")
    free = course(trainer(), modules=(("A", 1),), quiz=1)
    student = signed_in(student_user)
    student.post(reverse("v1:academy-get", args=[free.slug]), {}, format="json", **H)
    module = free.modules.first()
    lesson = module.lessons.first()

    played = student.get(reverse("v1:academy-lesson", args=[lesson.pk])).json()
    assert played["urls"]["low"] and played["quiz_after"] == str(module.pk)
    assert played["next"] is None and played["course_slug"] == free.slug
    position = student.post(
        reverse("v1:academy-position", args=[lesson.pk]), {"seconds": 240}, format="json", **H
    ).json()
    assert position["progress_percent"] == 50 and not position["completed"]

    quiz = student.get(reverse("v1:academy-quiz", args=[module.pk])).json()
    assert quiz["unlocked"] and "correct" not in quiz["questions"][0]
    result = student.post(
        reverse("v1:academy-quiz", args=[module.pk]), {"answers": [0]}, format="json", **H
    ).json()
    assert result["passed"] and result["progress"]["completed"]
    code = result["progress"]["certificate"]

    mine = student.get(reverse("v1:academy-me")).json()
    assert mine["courses"][0]["enrollment"]["certificate"] == code
    check = APIClient().get(reverse("v1:academy-certificate", args=[code])).json()
    assert check["valid"] and check["holder_name"] == "Awa"
    pdf = student.get(reverse("v1:academy-certificate-pdf", args=[code]))
    assert pdf.status_code == 200 and pdf["Content-Type"] == "application/pdf"
    other = signed_in(adult("Bintou")).get(reverse("v1:academy-certificate-pdf", args=[code]))
    assert other.status_code == 404
    assert APIClient().get(reverse("v1:academy-certificate", args=["NOPE"])).status_code == 404


def test_pass_and_lives():
    student_user = adult("Awa")
    student = signed_in(student_user)
    assert student.get(reverse("v1:academy-pass")).json()["price_minor"] is None
    setting("academy.pass_price_minor", 2000)
    offer = student.get(reverse("v1:academy-pass")).json()
    assert offer["price_minor"] == 2000 and offer["active"] is False
    assert student.post(reverse("v1:academy-pass-subscribe"), **H).json()["checkout_url"]

    pro = trainer()
    live = LiveSession.objects.create(
        pro=pro,
        author=pro.user,
        country=pro.country,
        title="Vos questions",
        starts_at=timezone.now() + datetime.timedelta(days=1),
        capacity=10,
    )
    listed = APIClient().get(reverse("v1:academy-lives"), {"country": "BJ"}).json()
    assert listed["results"][0]["places_left"] == 10
    registered = student.post(reverse("v1:academy-live-registration", args=[live.pk]), **H).json()
    assert registered["registered"] and registered["places_left"] == 9
    room = student.get(reverse("v1:academy-live", args=[live.pk])).json()
    assert room["registered"] and not room["open"] and room["broadcast_ready"] is False
    assert room["room_link"] == f"/live/training/{live.pk}"
    left = student.delete(reverse("v1:academy-live-registration", args=[live.pk]), **H).json()
    assert left["registered"] is False


def test_trainer_space_guided_creation():
    pro = trainer()
    me = signed_in(pro.user)
    created = me.post(
        reverse("v1:studio-courses"),
        {"title": "Tresses collées", "level": "beginner", "trade": "braids"},
        format="json",
        **H,
    ).json()
    assert created["status"] == "draft" and created["price_min"] == 500
    course_id = created["id"]
    with_module = me.post(
        reverse("v1:studio-modules", args=[course_id]), {"title": "Les raies"}, format="json", **H
    ).json()
    module_id = with_module["modules"][0]["id"]
    with_lesson = me.post(
        reverse("v1:studio-lessons", args=[module_id]),
        {"title": "Tracer une raie", "video_id": str(video(pro.user).pk)},
        format="json",
        **H,
    ).json()
    lesson_id = with_lesson["modules"][0]["lessons"][0]["id"]
    renamed = me.patch(
        reverse("v1:studio-lesson", args=[lesson_id]),
        {"title": "Tracer une raie droite", "is_preview": True},
        format="json",
        **H,
    ).json()
    lesson = renamed["modules"][0]["lessons"][0]
    assert lesson["title"] == "Tracer une raie droite" and lesson["video"]["status"] == "ready"
    with_question = me.post(
        reverse("v1:studio-questions", args=[module_id]),
        {"text": "On tire fort ?", "choices": ["Oui", "Non"], "correct": 1},
        format="json",
        **H,
    ).json()
    assert with_question["modules"][0]["questions"][0]["correct"] == 1
    priced = me.patch(
        reverse("v1:studio-course", args=[course_id]),
        {"pricing": "paid", "price_minor": 3000},
        format="json",
        **H,
    ).json()
    assert priced["pricing"] == "paid"
    sent = me.post(reverse("v1:studio-submit", args=[course_id]), **H).json()
    assert sent["status"] == "in_review"
    studio = me.get(reverse("v1:academy-studio")).json()
    assert studio["is_pro"] and studio["courses"][0]["stats"]["students"] == 0
    assert (
        signed_in(adult("Awa")).get(reverse("v1:studio-course", args=[course_id])).status_code
        == 404
    )

    live = me.post(
        reverse("v1:studio-lives"),
        {
            "title": "Vos questions",
            "starts_at": (timezone.now() + datetime.timedelta(days=2)).isoformat(),
            "duration_minutes": 45,
            "capacity": 30,
        },
        format="json",
        **H,
    )
    assert live.status_code == 201
    cancelled = me.post(reverse("v1:studio-live-cancel", args=[live.json()["id"]]), **H).json()
    assert cancelled["status"] == "cancelled"


def test_search_shows_the_badge_and_puts_trained_pros_first():
    plain = trainer("Awa", rating_average=4)
    trained = trainer("Bintou", rating_average=4)
    ProProfile.objects.filter(pk=trained.pk).update(trained_at=timezone.now())
    results = APIClient().get(reverse("v1:pros-search")).json()["results"]
    slugs = [r["slug"] for r in results]
    assert slugs.index(trained.slug) < slugs.index(plain.slug)
    assert next(r for r in results if r["slug"] == trained.slug)["trained"] is True
    only = APIClient().get(reverse("v1:pros-search"), {"trained": "true"}).json()["results"]
    assert [r["slug"] for r in only] == [trained.slug]


@pytest.fixture
def team(client):
    admin = UserFactory(is_staff=True, is_superuser=True)
    client.force_login(admin)
    return client


def test_admin_pages_and_the_review_queue(team):
    pro = trainer()
    waiting = course(pro, status=Course.Status.IN_REVIEW)
    published = course(pro)
    for name in (
        "academy_course",
        "academy_coursereview",
        "academy_enrollment",
        "academy_certificate",
        "academy_academypass",
        "academy_livesession",
    ):
        assert team.get(reverse(f"admin:{name}_changelist")).status_code == 200
    queue = team.get(reverse("admin:academy_coursereview_changelist")).content.decode()
    assert waiting.slug in queue or waiting.title in queue
    assert team.get(reverse("admin:academy_course_change", args=[waiting.pk])).status_code == 200

    team.get(reverse("admin:academy_coursereview_publish_detail", args=[waiting.pk]))
    waiting.refresh_from_db()
    assert waiting.status == Course.Status.PUBLISHED

    form = reverse("admin:academy_course_send_back_detail", args=[published.pk])
    assert team.get(form).status_code == 200
    team.post(form, {"note": "Le son est trop bas."})
    published.refresh_from_db()
    assert (published.status, published.review_note) == (
        Course.Status.REJECTED,
        "Le son est trop bas.",
    )

    student = adult("Awa")
    from apps.academy.services import enrollments, progress

    enrollments.get_course(student, waiting)
    for lesson in waiting.modules.first().lessons.all():
        progress.save_position(student, lesson, seconds=240, ended=True)
    certificate = Certificate.objects.get()
    revoke = reverse("admin:academy_certificate_revoke_detail", args=[certificate.pk])
    assert team.get(revoke).status_code == 200
    team.post(revoke, {"reason": "Erreur"})
    certificate.refresh_from_db()
    assert not certificate.is_valid
    assert Group.objects.filter(name="Academy review").exists()


def test_platform_course_needs_the_team():
    member = adult("Équipe", is_staff=True, is_superuser=True)
    me = signed_in(member)
    created = me.post(
        reverse("v1:studio-courses"),
        {"title": "Hygiène", "platform": True, "country": "BJ", "pricing": "pass"},
        format="json",
        **H,
    ).json()
    assert created["trainer"]["platform"] is True
    other = signed_in(adult("Awa")).post(
        reverse("v1:studio-courses"),
        {"title": "Non", "platform": True, "country": "BJ"},
        format="json",
        **H,
    )
    assert other.status_code == 403
