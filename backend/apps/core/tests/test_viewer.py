"""One rule for the country whose content a person sees (apps/core/viewer.py)."""

import pytest
from django.test import RequestFactory

from apps.core.viewer import viewer_country
from apps.social.models import Follow
from apps.social.tests.factories import person, published_post

from .factories import CountryFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def countries():
    return CountryFactory(code="BJ", name="Bénin"), CountryFactory(code="FR", name="France")


def request(header=None, user=None):
    made = RequestFactory().get("/", **({"HTTP_X_SG_COUNTRY": header} if header else {}))
    if user is not None:
        made.user = user
    return made


def test_asked_then_device_then_account_then_everywhere(countries):
    benin, france = countries
    awa = person("Awa", country=benin)
    assert viewer_country(request("FR", awa)) == france
    assert viewer_country(request("FR", awa), asked="BJ") == benin
    assert viewer_country(request("*", awa)) is None
    assert viewer_country(request(user=awa)) == benin
    assert viewer_country(request("ZZ")) is None


def test_the_feed_shows_her_country_and_the_people_she_follows(api_client, countries):
    benin, france = countries
    cotonou = published_post(person("Aïcha", country=benin), caption="Tresses à Cotonou")
    paris = published_post(person("Inès", city="Paris", country=france), caption="Brushing à Paris")

    def captions(**headers):
        page = api_client.get("/api/v1/feed", **headers).json()
        return {post["caption"] for post in page["results"]}

    nowhere = published_post(person("Lou", country=None), caption="Sans pays")
    assert captions(HTTP_X_SG_COUNTRY="BJ") == {cotonou.caption, nowhere.caption}
    assert captions(HTTP_X_SG_COUNTRY="FR") == {paris.caption, nowhere.caption}
    assert captions(HTTP_X_SG_COUNTRY="*") == {cotonou.caption, paris.caption, nowhere.caption}

    # Someone she follows shows up wherever she lives.
    awa = person("Awa", country=benin)
    Follow.objects.create(follower=awa, followed=paris.author)
    api_client.force_authenticate(awa)
    assert captions() == {cotonou.caption, paris.caption, nowhere.caption}
