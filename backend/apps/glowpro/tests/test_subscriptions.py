"""Glow Pro: the free plan and its limits, the trial, paying a month, renewal, grace, back
to free (nothing deleted, extra people paused)."""

import datetime

import pytest
from django.utils import timezone

from apps.booking.models import StaffMember
from apps.booking.services import agenda
from apps.booking.tests.factories import salon
from apps.glowpro import errors, selectors, services
from apps.glowpro.models import Feature, Subscription, Widget
from apps.invoicing.models import Document
from apps.notifications.models import Notification
from apps.payments import services as payments
from apps.payments.models import Payment

from .factories import premium, priced

pytestmark = pytest.mark.django_db
S = Subscription.Status


@pytest.fixture
def clock(monkeypatch):
    class Clock:
        value = timezone.now()

        def move(self, **delta):
            self.value = self.value + datetime.timedelta(**delta)

    found = Clock()
    monkeypatch.setattr(timezone, "now", lambda: found.value)
    return found


def fresh(pro):
    pro.__dict__.pop("_glowpro_subscription", None)
    return pro


def pay(payment: Payment) -> Payment:
    payments.mark_paid(
        payment, amount_minor=payment.total_minor, currency=payment.currency, key=str(payment.pk)
    )
    return Payment.objects.get(pk=payment.pk)


def events(user):
    return list(Notification.objects.filter(user=user).values_list("event_key", flat=True))


def test_the_free_plan_has_two_people_besides_the_pro():
    pro = salon()
    assert selectors.plan_of(pro).key == "free"
    assert not selectors.has_feature(pro, Feature.STOCK)
    agenda.save_staff(pro, name="Carine")
    agenda.save_staff(pro, name="Sika")
    with pytest.raises(errors.StaffLimit) as limit:
        agenda.save_staff(pro, name="Joëlle")
    assert limit.value.details == {"limit": 2}
    with pytest.raises(errors.PremiumRequired):
        selectors.require(pro, Feature.CAMPAIGNS)


def test_the_trial_unlocks_everything_once():
    pro = salon()
    subscription = services.start_trial(pro)
    assert subscription.status == S.TRIALING and subscription.trial_used
    end = timezone.localdate(subscription.current_period_end)
    assert end == timezone.localdate() + datetime.timedelta(days=30)
    assert selectors.has_feature(fresh(pro), Feature.STOCK)
    for name in ("Carine", "Sika", "Joëlle"):
        agenda.save_staff(pro, name=name)
    assert "glowpro.trial_started" in events(pro.user)
    with pytest.raises(errors.AlreadyPremium):
        services.start_trial(pro)


def test_paying_a_month_goes_to_the_platform_at_once_with_an_invoice():
    pro = salon()
    priced(pro)
    payment = services.subscribe(pro)
    assert payment.purpose == "subscription" and payment.items_minor == 9_900
    assert payment.buyer == pro.user and payment.seller == selectors.house_account(pro.country)
    assert payment.buyer_fee_minor == 0 and payment.commission_minor == 0
    paid = pay(payment)
    assert paid.status == Payment.Status.RELEASED
    subscription = Subscription.objects.get(pro=pro)
    assert subscription.status == S.ACTIVE and subscription.renewal_payment is None
    end = timezone.localdate(subscription.current_period_end)
    assert end == services.add_month(timezone.now()).date()
    invoice = Document.objects.get(source_type="glowpro", source_id=payment.pk)
    assert invoice.issuer.is_platform and invoice.total_minor == 9_900
    assert invoice.number == f"F-{timezone.now().year}-000001"
    assert "glowpro.paid" in events(pro.user)
    with pytest.raises(errors.AlreadyPremium):
        services.subscribe(pro)


def test_renewal_grace_then_back_to_free(clock):
    pro = salon()
    priced(pro)
    pay(services.subscribe(pro))
    for name in ("Carine", "Sika", "Joëlle"):
        agenda.save_staff(fresh(pro), name=name)
    Widget.objects.create(pro=pro, allowed_domains=["salon.fr"])
    clock.move(days=29)
    assert services.send_renewals() == 1
    subscription = Subscription.objects.get(pro=pro)
    assert subscription.renewal_payment.status == Payment.Status.PENDING_PAYMENT
    assert "glowpro.renewal_due" in events(pro.user)
    assert services.send_renewals() == 0  # once
    clock.move(days=3)
    assert services.end_periods() == {"past_due": 1, "ended": 0}
    assert selectors.plan_of(fresh(pro)).key == "premium"  # days of grace
    clock.move(days=8)
    assert services.end_periods() == {"past_due": 0, "ended": 1}
    subscription.refresh_from_db()
    assert subscription.status == S.ENDED and selectors.plan_of(fresh(pro)).key == "free"
    active = StaffMember.objects.filter(pro=pro, is_owner=False, is_active=True)
    assert [m.name for m in active] == ["Carine", "Sika"]  # Joëlle paused, not deleted
    assert StaffMember.objects.filter(pro=pro).count() == 4
    assert not Widget.objects.get(pro=pro).is_active
    unpaid = Payment.objects.filter(buyer=pro.user, purpose="subscription").latest("created_at")
    assert unpaid.status == Payment.Status.CANCELLED  # the unpaid month is closed


def test_paying_during_grace_starts_a_new_month(clock):
    pro = salon()
    priced(pro)
    pay(services.subscribe(pro))
    clock.move(days=32)
    services.send_renewals()
    services.end_periods()
    subscription = Subscription.objects.get(pro=pro)
    assert subscription.status == S.PAST_DUE
    pay(subscription.renewal_payment)
    subscription.refresh_from_db()
    assert subscription.status == S.ACTIVE and subscription.current_period_end > timezone.now()
    assert subscription.periods.count() == 2


def test_cancel_stops_at_the_end_of_the_month(clock):
    pro = salon()
    premium(pro)
    services.cancel(pro)
    assert services.send_renewals() == 0  # nothing to pay for a cancelled one
    clock.move(days=32)
    assert services.end_periods()["ended"] == 1
    assert selectors.plan_of(fresh(pro)).key == "free"


def test_trial_end_notice_then_end(clock):
    pro = salon()
    services.start_trial(pro)
    clock.move(days=28)
    assert services.send_renewals() == 1
    assert "glowpro.trial_ending" in events(pro.user)
    clock.move(days=3)
    assert services.run_all()["ended"] == 1


def test_months_of_different_lengths():
    moment = datetime.datetime(2027, 1, 31, 10, tzinfo=datetime.UTC)
    assert services.add_month(moment).date() == datetime.date(2027, 2, 28)
    assert services.add_month(datetime.datetime(2027, 12, 15, tzinfo=datetime.UTC)).month == 1
    # 23:30 UTC on 31 January is already 1 February in Paris.
    late = datetime.datetime(2027, 1, 31, 23, 30, tzinfo=datetime.UTC)
    assert services.add_month(late).date() == datetime.date(2027, 3, 1)


def test_a_trial_started_after_midnight_keeps_its_last_day(clock):
    # 00:20 in Paris, five days before the change to winter time.
    clock.value = datetime.datetime(2026, 10, 20, 22, 20, tzinfo=datetime.UTC)
    subscription = services.start_trial(salon())
    end = timezone.localtime(subscription.current_period_end)
    assert (end.date(), end.hour, end.minute) == (datetime.date(2026, 11, 20), 0, 20)


def test_widget_settings_need_premium():
    pro = salon()
    with pytest.raises(errors.PremiumRequired):
        services.save_widget(pro, color="#7A3E9D", allowed_domains=["salon.fr"])
    premium(pro)
    widget = services.save_widget(
        fresh(pro),
        color="#7A3E9D",
        allowed_domains=["https://www.Salon-Estelle.fr/rdv", "salon.fr"],
    )
    assert widget.allowed_domains == ["salon.fr", "www.salon-estelle.fr"]
    assert services.widget_for(pro.slug) == widget
    with pytest.raises(errors.InvalidWidget):
        services.save_widget(pro, color="red", allowed_domains=[])
