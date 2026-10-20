"""Demo agendas on a new database (the end-to-end journeys rely on them)."""

import pytest
from django.core.management import call_command

from apps.booking.models import BookingSettings, StaffMember

pytestmark = pytest.mark.django_db


def test_demo_agendas_on_a_new_database():
    call_command("seed_demo", "--force", verbosity=0)
    assert BookingSettings.objects.get(pro__slug="bene-coiffure").auto_confirm is False
    assert BookingSettings.objects.get(pro__slug="institut-prisca").auto_confirm is True
    assert StaffMember.objects.filter(pro__slug="institut-prisca").count() == 4
    call_command("seed_demo", "--force", verbosity=0)  # idempotent
    assert StaffMember.objects.filter(pro__slug="institut-prisca").count() == 4
