import pytest

from apps.core.choices import Role
from apps.core.selectors import is_feature_enabled

from .factories import CountryFactory, FeatureFlagFactory

pytestmark = pytest.mark.django_db


def test_unknown_or_disabled_flag_is_off():
    FeatureFlagFactory(key="beta_feature", is_enabled=False)

    assert is_feature_enabled("unknown") is False
    assert is_feature_enabled("beta_feature") is False


def test_flag_without_restrictions_is_on_for_everyone():
    FeatureFlagFactory(key="beta_feature")

    assert is_feature_enabled("beta_feature") is True
    assert is_feature_enabled("beta_feature", country="FR", roles=[Role.PRO]) is True


def test_flag_limited_by_country_and_role():
    flag = FeatureFlagFactory(key="beta_module", roles=[Role.PRO])
    flag.countries.add(CountryFactory(code="BJ"))

    assert is_feature_enabled("beta_module", country="BJ", roles=[Role.PRO]) is True
    assert is_feature_enabled("beta_module", country="FR", roles=[Role.PRO]) is False
    assert is_feature_enabled("beta_module", country="BJ", roles=[Role.CLIENT]) is False


def test_flag_cache_follows_changes():
    flag = FeatureFlagFactory(key="test-cache")
    assert is_feature_enabled("test-cache") is True

    flag.is_enabled = False
    flag.save()
    assert is_feature_enabled("test-cache") is False

    flag.is_enabled = True
    flag.save()
    flag.countries.add(CountryFactory(code="BJ"))
    assert is_feature_enabled("test-cache", country="FR") is False
