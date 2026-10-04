from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.core.models import PlatformSetting
from apps.core.selectors import SettingNotFound, get_setting

from .factories import CountryFactory, CurrencyFactory, PlatformSettingFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def benin():
    return CountryFactory(code="BJ")


@pytest.fixture
def france():
    return CountryFactory(
        code="FR",
        name="France",
        phone_prefix="+33",
        default_currency=CurrencyFactory(code="EUR", symbol="€", decimal_places=2),
    )


def test_global_value_without_country():
    PlatformSettingFactory(key="escrow.ship_deadline_days", value="3")

    assert get_setting("escrow.ship_deadline_days") == 3


def test_country_value_overrides_global(benin, france):
    PlatformSettingFactory(key="escrow.ship_deadline_days", value="3")
    PlatformSettingFactory(key="escrow.ship_deadline_days", value="5", country=france)

    assert get_setting("escrow.ship_deadline_days", country="FR") == 5
    assert get_setting("escrow.ship_deadline_days", country=france) == 5
    assert get_setting("escrow.ship_deadline_days", country="fr") == 5


def test_country_without_override_falls_back_to_global(benin, france):
    PlatformSettingFactory(key="escrow.ship_deadline_days", value="3")
    PlatformSettingFactory(key="escrow.ship_deadline_days", value="5", country=france)

    assert get_setting("escrow.ship_deadline_days", country=benin) == 3
    assert get_setting("escrow.ship_deadline_days") == 3


def test_country_only_value_is_not_used_globally(france):
    PlatformSettingFactory(key="shop.fee", value="2", country=france)

    assert get_setting("shop.fee", country="FR") == 2
    with pytest.raises(SettingNotFound):
        get_setting("shop.fee")


def test_missing_setting_raises_or_returns_default():
    with pytest.raises(SettingNotFound):
        get_setting("does.not_exist")
    assert get_setting("does.not_exist", default=None) is None
    assert get_setting("does.not_exist", country="BJ", default=7) == 7


@pytest.mark.parametrize(
    ("value_type", "raw", "expected"),
    [
        (PlatformSetting.ValueType.STRING, " hello ", "hello"),
        (PlatformSetting.ValueType.INTEGER, "42", 42),
        (PlatformSetting.ValueType.DECIMAL, "12.5", Decimal("12.5")),
        (PlatformSetting.ValueType.BOOLEAN, "true", True),
        (PlatformSetting.ValueType.BOOLEAN, "False", False),
        (PlatformSetting.ValueType.JSON, '{"a": [1, 2]}', {"a": [1, 2]}),
    ],
)
def test_values_are_typed(value_type, raw, expected):
    PlatformSettingFactory(key="typed.value", value_type=value_type, value=raw)

    assert get_setting("typed.value") == expected


def test_invalid_value_fails_validation():
    setting = PlatformSettingFactory.build(
        key="typed.value", value_type=PlatformSetting.ValueType.INTEGER, value="three"
    )
    with pytest.raises(ValidationError) as excinfo:
        setting.full_clean()
    assert "value" in excinfo.value.message_dict


def test_cache_is_invalidated_on_save_and_delete(django_assert_num_queries):
    setting = PlatformSettingFactory(key="escrow.auto_release_days", value="7")
    assert get_setting("escrow.auto_release_days") == 7

    with django_assert_num_queries(0):
        assert get_setting("escrow.auto_release_days") == 7

    setting.value = "10"
    setting.save()
    assert get_setting("escrow.auto_release_days") == 10

    setting.delete()
    assert get_setting("escrow.auto_release_days", default=None) is None


def test_key_and_country_pair_is_unique():
    PlatformSettingFactory(key="unique.key", value="1")
    duplicate = PlatformSettingFactory.build(key="unique.key", value="2")
    with pytest.raises(ValidationError):
        duplicate.full_clean()
