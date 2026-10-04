import pytest
from django.core.management import call_command

from apps.core.models import Country, Currency, PlatformSetting
from apps.core.selectors import get_setting

pytestmark = pytest.mark.django_db


def test_seed_core_creates_reference_data():
    call_command("seed_core", verbosity=0)

    assert set(Currency.objects.values_list("code", flat=True)) == {"XOF", "EUR"}
    assert set(Country.objects.values_list("code", flat=True)) == {"BJ", "FR"}
    assert Country.objects.get(code="BJ").default_currency.code == "XOF"
    assert Currency.objects.get(code="EUR").decimal_places == 2
    assert get_setting("escrow.ship_deadline_days", country="BJ") == 3
    assert get_setting("escrow.ship_deadline_days", country="FR") == 3
    assert get_setting("escrow.auto_release_days") == 7
    assert get_setting("escrow.auto_dispute_days") == 7
    assert get_setting("escrow.dispute_response_hours") == 48


def test_seed_core_is_idempotent_and_keeps_admin_edits():
    call_command("seed_core", verbosity=0)
    setting = PlatformSetting.objects.get(key="escrow.auto_release_days")
    setting.value = "10"
    setting.save()

    call_command("seed_core", verbosity=0)

    assert Currency.objects.count() == 2
    assert Country.objects.count() == 2
    assert PlatformSetting.objects.filter(key__startswith="escrow.").count() == 6
    assert get_setting("escrow.auto_release_days") == 10
