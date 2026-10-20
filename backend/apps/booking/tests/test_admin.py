"""Back office: every booking list opens, an appointment is cancelled with a refund."""

import pytest
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.booking.models import Appointment, StaffMember
from apps.booking.services import appointments, groups, waitlist
from apps.messaging.tests.factories import adult
from apps.payments.models import Payment

from .factories import MONDAY, at, person, salon, service

pytestmark = pytest.mark.django_db


@pytest.fixture
def team(client):
    client.force_login(UserFactory(is_staff=True, is_superuser=True))
    return client


def test_lists_and_pages_open(team):
    pro = salon()
    person(pro, "Carine")
    svc = service(pro, ("work", 60))
    booked = appointments.book(pro, svc.pk, at(10), user=adult(phone="+2290197000055"))
    assert booked.client_phone
    groups.create_group(adult("Mireille"), pro, svc.pk, at(14), 2)
    waitlist.join(pro, svc.pk, MONDAY, user=adult("Inès"))
    for name in (
        "appointment",
        "staffmember",
        "bookingsettings",
        "timeoff",
        "resource",
        "waitlistentry",
        "groupbooking",
        "clientrecord",
        "lastminuteoffer",
    ):
        assert team.get(reverse(f"admin:booking_{name}_changelist")).status_code == 200
    page = team.get(reverse("admin:booking_appointment_change", args=[booked.pk]))
    assert page.status_code == 200 and booked.client_phone.encode() not in page.content
    staff = StaffMember.objects.filter(pro=pro, is_owner=False).get()
    assert team.get(reverse("admin:booking_staffmember_change", args=[staff.pk])).status_code == 200


def test_cancel_and_refund_in_one_click(team):
    pro = salon()
    svc = service(pro, ("work", 60), deposit_kind="amount", deposit_value=5_000)
    booked = appointments.book(pro, svc.pk, at(10), user=adult())
    payment = Payment.objects.get(pk=booked.payment_id)
    from apps.payments import services as payments

    payments.mark_paid(payment, amount_minor=payment.total_minor, currency="XOF", key="admin")
    team.get(reverse("admin:booking_appointment_cancel_detail", args=[booked.pk]))
    booked.refresh_from_db()
    assert booked.status == Appointment.Status.CANCELLED and booked.cancelled_by == "system"
    assert Payment.objects.get(pk=payment.pk).status == "refunded"
