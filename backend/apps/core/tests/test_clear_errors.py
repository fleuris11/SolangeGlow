"""What a person reads when something goes wrong: clear words, never technical ones."""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from rest_framework import exceptions
from rest_framework.test import APIClient

from apps.core.api.exceptions import exception_handler

pytestmark = pytest.mark.django_db
TECHNICAL = ("CSRF", "token", "credentials", "Traceback", "throttled", "Authentication")


def _user(**values):
    return get_user_model().objects.create_superuser(
        email="proprio@example.com", password="demo-Glow-2026", **values
    )


def test_someone_signed_in_to_the_admin_is_never_asked_for_a_csrf_token():
    client = Client(enforce_csrf_checks=True)
    client.force_login(_user())
    answer = client.post(
        reverse("v1:logout"), content_type="application/json", HTTP_X_SG_CLIENT="web"
    )
    assert "CSRF" not in answer.content.decode()


def test_a_visitor_is_told_to_sign_in():
    answer = APIClient().get(reverse("v1:agenda"))
    assert answer.status_code == 401
    body = answer.json()
    assert not any(word in body["message"] for word in TECHNICAL)
    assert body["fields"] == {}


@pytest.mark.parametrize(
    "error",
    [
        exceptions.NotAuthenticated(),
        exceptions.AuthenticationFailed("Token is invalid or expired"),
        exceptions.PermissionDenied("CSRF Failed: CSRF token missing."),
        exceptions.NotFound("No Appointment matches the given query."),
        exceptions.Throttled(wait=30),
        exceptions.MethodNotAllowed("POST"),
        exceptions.UnsupportedMediaType("text/plain"),
        exceptions.ParseError("JSON parse error"),
    ],
)
def test_no_framework_message_reaches_the_person(error):
    message = exception_handler(error, {}).data["message"]
    assert message
    assert not any(word.lower() in message.lower() for word in TECHNICAL)
    assert str(error.detail) != message


def test_a_bug_gives_a_clear_answer_and_is_logged(caplog):
    answer = exception_handler(ValueError("secret detail"), {})
    assert answer.status_code == 500
    assert answer.data["code"] == "server_error"
    assert "secret" not in answer.data["message"]
    assert "Unexpected error" in caplog.text
