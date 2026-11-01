"""Every address of the API that names an object: a stranger never gets someone else's
object (200) and never breaks the server (500), signed in or not."""

import re
import uuid

import pytest
from django.urls import get_resolver
from rest_framework.test import APIClient

from apps.messaging.tests.factories import adult

pytestmark = pytest.mark.django_db
PARAM = re.compile(r"<(?:(\w+):)?(\w+)>")


def _routes():
    def walk(patterns, prefix=""):
        for pattern in patterns:
            if hasattr(pattern, "url_patterns"):
                yield from walk(pattern.url_patterns, prefix + str(pattern.pattern))
            else:
                yield prefix + str(pattern.pattern)

    for route in walk(get_resolver().url_patterns):
        params = PARAM.findall(route)
        if route.startswith("api/v1/") and params and all(c == "uuid" for c, _ in params):
            yield "/" + PARAM.sub(lambda _m: str(uuid.uuid4()), route).replace("^", "").rstrip("$")


ROUTES = sorted(set(_routes()))


def _is_empty(response) -> bool:
    try:
        body = response.json()
    except ValueError:
        return False
    if isinstance(body, dict):
        return all(not value for key, value in body.items() if key not in ("next", "previous"))
    return not body


def test_there_are_many_routes_to_check():
    assert len(ROUTES) > 50


@pytest.mark.parametrize("signed_in", [False, True])
def test_a_stranger_gets_nothing_and_breaks_nothing(signed_in):
    client = APIClient()
    if signed_in:
        client.force_authenticate(adult("Stranger"))
    wrong = []
    for path in ROUTES:
        for method in ("get", "delete"):
            response = getattr(client, method)(path, HTTP_X_SG_CLIENT="web")
            # An empty public list (reviews of an unknown product) gives nothing away.
            empty = response.status_code == 200 and _is_empty(response)
            if (response.status_code == 200 and not empty) or response.status_code >= 500:
                wrong.append(f"{method.upper()} {path} {response.status_code}")
    assert wrong == []
