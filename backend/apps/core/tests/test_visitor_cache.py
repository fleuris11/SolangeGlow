import pytest
from django.test.utils import override_settings

from apps.content.models import FaqItem
from apps.messaging.tests.factories import adult

from .factories import PlatformSettingFactory

pytestmark = pytest.mark.django_db


def _questions(response) -> set[str]:
    return {item["question"] for topic in response.json() for item in topic["items"]}


def _faq(question: str) -> FaqItem:
    return FaqItem.objects.create(topic="account", question=question, answer="Answer.")


@override_settings(VISITOR_CACHE=True)
def test_visitors_share_one_answer_signed_in_people_get_a_fresh_one(api_client):
    _faq("First question")
    assert "First question" in _questions(api_client.get("/api/v1/help/faq"))

    _faq("Second question")
    # A visitor gets the answer kept a few seconds ago.
    assert "Second question" not in _questions(api_client.get("/api/v1/help/faq"))

    # A signed-in person always gets a fresh one.
    api_client.force_authenticate(adult("Awa"))
    assert "Second question" in _questions(api_client.get("/api/v1/help/faq"))


@override_settings(VISITOR_CACHE=True)
def test_the_owner_can_turn_it_off(api_client):
    PlatformSettingFactory(key="performance.visitor_cache_seconds", value="0")
    _faq("First question")
    api_client.get("/api/v1/help/faq")
    _faq("Second question")
    assert "Second question" in _questions(api_client.get("/api/v1/help/faq"))


def test_off_in_development_and_tests(api_client):
    _faq("First question")
    api_client.get("/api/v1/help/faq")
    _faq("Second question")
    assert "Second question" in _questions(api_client.get("/api/v1/help/faq"))
