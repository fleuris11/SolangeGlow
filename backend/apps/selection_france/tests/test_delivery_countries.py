"""The countries where the France Selection delivers are ticked in the back-office console,
and the app names them (« Delivery open now: Benin »)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.core.selectors import get_setting
from apps.core.tests.factories import CountryFactory
from apps.selection_france import selectors

pytestmark = pytest.mark.django_db
LIST = "/api/v1/selection/products"


def test_countries_ticked_in_the_console_are_named_by_the_app(client):
    CountryFactory(code="BJ", name="Bénin", is_active=True)
    CountryFactory(code="FR", name="France", is_active=True)
    CountryFactory(code="TG", name="Togo", is_active=False)
    assert APIClient().get(LIST).json()["delivery_countries"] == [{"code": "BJ", "name": "Bénin"}]

    owner = get_user_model().objects.create_superuser(
        email="owner@example.com", password="s3c-ret1"
    )
    client.force_login(owner)
    console = reverse("admin:backoffice_selection_console")
    page = client.get(console)
    assert page.status_code == 200 and "France" in page.content.decode()
    # An inactive or unknown country is ignored, whatever the form sends.
    saved = client.post(console, {"countries": ["BJ", "FR", "TG", "XX"]})
    assert saved.status_code == 302
    assert get_setting("selection.countries") == ["BJ", "FR"]
    assert selectors.delivery_country_codes() == ["BJ", "FR"]
    names = [c["name"] for c in APIClient().get(LIST).json()["delivery_countries"]]
    assert names == ["Bénin", "France"]

    client.post(console, {})
    assert APIClient().get(LIST).json()["delivery_countries"] == []
