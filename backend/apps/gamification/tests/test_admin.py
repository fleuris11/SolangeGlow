"""The « Games » section of the back office: every list opens, a quiz and a challenge are
approved in one click, points are given or taken back in the ledger."""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.gamification.models import Challenge, GlowProfile, PointsEntry, QuizDay, QuizQuestion
from apps.gamification.services import points
from apps.messaging.tests.factories import adult

pytestmark = pytest.mark.django_db
MODELS = [
    "glowprofile",
    "pointsentry",
    "reward",
    "voucher",
    "wheelprize",
    "wheelspin",
    "quizday",
    "challenge",
    "poll",
    "ranking",
    "referral",
    "celebration",
]


@pytest.fixture
def admin_client(client):
    user = get_user_model().objects.create_superuser(
        email="owner@example.com", password="s3cret-pass"
    )
    client.force_login(user)
    return client


@pytest.mark.parametrize("model", MODELS)
def test_every_list_opens(admin_client, model):
    assert admin_client.get(reverse(f"admin:gamification_{model}_changelist")).status_code == 200


@pytest.mark.parametrize("model", ["reward", "wheelprize", "quizday", "challenge", "celebration"])
def test_every_form_opens(admin_client, model):
    assert admin_client.get(reverse(f"admin:gamification_{model}_add")).status_code == 200


def test_a_quiz_is_written_in_three_languages_and_approved_in_one_click(admin_client):
    quiz = QuizDay.objects.create(date=datetime.date(2026, 12, 1))
    page = admin_client.get(reverse("admin:gamification_quizday_change", args=[quiz.pk]))
    html = page.content.decode()
    assert "text_fr" in html and "text_en" in html and "text_sk" in html
    assert "image_upload" in html and "audio_upload" in html
    refused = admin_client.get(
        reverse("admin:gamification_quizday_approve_detail", args=[quiz.pk]), follow=True
    )
    assert refused.status_code == 200
    quiz.refresh_from_db()
    assert quiz.status == "draft"
    for n in range(3):
        QuizQuestion.objects.create(
            quiz=quiz, position=n, text=f"Q{n}", choice_1="Oui", choice_2="Non", answer=1
        )
    admin_client.get(reverse("admin:gamification_quizday_approve_detail", args=[quiz.pk]))
    quiz.refresh_from_db()
    assert quiz.status == "approved"


def test_a_challenge_approved_in_one_click(admin_client):
    challenge = Challenge.objects.create(
        theme="Look pagne",
        starts_on=datetime.date(2026, 11, 9),
        ends_on=datetime.date(2026, 11, 15),
    )
    admin_client.get(reverse("admin:gamification_challenge_approve_detail", args=[challenge.pk]))
    challenge.refresh_from_db()
    assert challenge.status == "approved"


def test_points_given_and_taken_back_from_the_profile(admin_client):
    awa = adult()
    points.summary(awa)
    profile = GlowProfile.objects.get(user=awa)
    url = reverse("admin:gamification_glowprofile_adjust_detail", args=[profile.pk])
    assert admin_client.get(url).status_code == 200
    admin_client.post(url, {"amount": 120, "note": "Concours"})
    admin_client.post(url, {"amount": -500, "note": "Trop"})
    assert points.balance(awa) == 120
    assert PointsEntry.objects.filter(user=awa).count() == 1
    page = admin_client.get(reverse("admin:gamification_glowprofile_change", args=[profile.pk]))
    assert page.status_code == 200
