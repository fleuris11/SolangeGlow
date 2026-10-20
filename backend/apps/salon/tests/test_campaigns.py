"""Campaigns: segments, only clients who said yes, unsubscribe link, statistics, limit."""

import datetime

import pytest
from django.core import mail
from django.utils import timezone

from apps.booking.models import ClientRecord
from apps.booking.services import appointments
from apps.booking.tests.factories import at, salon, service
from apps.glowpro import errors as glowpro_errors
from apps.glowpro.tests.factories import premium
from apps.messaging.tests.factories import adult
from apps.salon import errors
from apps.salon.models import Campaign, CampaignMessage, MarketingConsent
from apps.salon.services import campaigns

pytestmark = pytest.mark.django_db


@pytest.fixture
def clock(monkeypatch):
    class Clock:
        value = at(8, day=datetime.date(2030, 1, 5))

        def set(self, moment):
            self.value = moment

    found = Clock()
    monkeypatch.setattr(timezone, "now", lambda: found.value)
    return found


def done(pro, svc, user, clock, day):
    booked = appointments.book(pro, svc.pk, at(10, day=day), user=user)
    clock.set(at(12, day=day))
    appointments.complete(booked, actor=pro.user)
    return ClientRecord.objects.get(pro=pro, client=user)


def campaign(pro, **values):
    data = {
        "name": "On te manque",
        "segment": "inactive",
        "inactive_days": 30,
        "channel": "email",
        "subject": "Un soin offert, {{ first_name }} ?",
        "body": "Bonjour {{ first_name }}, {{ pro }} t'attend.",
        **values,
    }
    return campaigns.save_campaign(pro, **data)


def test_campaigns_are_premium():
    with pytest.raises(glowpro_errors.PremiumRequired):
        campaign(salon())


def test_only_consenting_clients_of_the_segment_receive_it(clock):
    pro = salon()
    premium(pro, days=400)
    svc = service(pro, ("work", 60))
    old = done(pro, svc, adult("Awa", email="awa@example.com"), clock, datetime.date(2030, 1, 7))
    no_consent = done(
        pro, svc, adult("Inès", email="ines@example.com"), clock, datetime.date(2030, 1, 8)
    )
    recent = done(
        pro, svc, adult("Sika", email="sika@example.com"), clock, datetime.date(2030, 3, 1)
    )
    for item in (old, recent):
        campaigns.set_consent(item, "email", True, source=MarketingConsent.Source.BOOKING)
    campaigns.set_consent(no_consent, "email", False, source="pro")
    clock.set(at(9, day=datetime.date(2030, 3, 10)))
    sent = campaigns.send(campaign(pro), actor=pro.user)
    assert sent.status == Campaign.Status.SENT
    assert (sent.targeted, sent.without_consent) == (2, 1)  # Awa and Inès are inactive
    assert [m.to for m in mail.outbox] == [["awa@example.com"]]
    message = mail.outbox[0]
    assert message.subject == "Un soin offert, Awa ?" and "/desabonnement/" in message.body
    assert "List-Unsubscribe" in message.extra_headers
    assert campaigns.stats(sent)["sent"] == 1
    with pytest.raises(errors.CampaignSent):
        campaigns.send(sent)


def test_unsubscribe_link_and_statistics(clock):
    pro = salon()
    premium(pro, days=400)
    svc = service(pro, ("work", 60))
    client = adult("Awa", email="awa@example.com")
    item = done(pro, svc, client, clock, datetime.date(2030, 1, 7))
    campaigns.set_consent(item, "email", True, source="booking")
    clock.set(at(9, day=datetime.date(2030, 3, 10)))
    sent = campaigns.send(campaign(pro), actor=pro.user)
    token = campaigns.unsubscribe_token(item, "email")
    found, channel = campaigns.unsubscribe(token)
    assert found == item and channel == "email"
    assert campaigns.consents_of(item) == {"email": False}
    appointments.book(pro, svc.pk, at(10, day=datetime.date(2030, 3, 12)), user=client)
    stats = campaigns.stats(sent)
    assert stats["unsubscribed"] == 1 and stats["returned"] == 1
    with pytest.raises(errors.InvalidUnsubscribe):
        campaigns.unsubscribe("tampered")


def test_segments_birthday_and_package(clock):
    pro = salon()
    premium(pro, days=400)
    svc = service(pro, ("work", 60))
    birthday = done(
        pro,
        svc,
        adult("Awa", birth_date=datetime.date(1995, 1, 9)),
        clock,
        datetime.date(2030, 1, 7),
    )
    ClientRecord.objects.filter(pk=birthday.pk).update()
    clock.set(at(9, day=datetime.date(2030, 1, 5)))
    assert list(campaigns.segment(pro, "birthday")) == [birthday]
    assert list(campaigns.segment(pro, "package_low")) == []


def test_whatsapp_not_configured_is_counted_as_not_sent(clock, settings):
    settings.PROVIDERS_CONSOLE = False
    settings.DEBUG = False
    pro = salon()
    premium(pro, days=400)
    svc = service(pro, ("work", 60))
    item = done(pro, svc, adult("Awa", phone="+2290197000055"), clock, datetime.date(2030, 1, 7))
    campaigns.set_consent(item, "whatsapp", True, source="booking")
    clock.set(at(9, day=datetime.date(2030, 3, 10)))
    sent = campaigns.send(campaign(pro, channel="whatsapp", subject=""), actor=pro.user)
    assert campaigns.stats(sent)["failed"] == 1
    assert CampaignMessage.objects.get(campaign=sent).error


def test_a_limit_of_campaigns_a_month(clock):
    pro = salon()
    premium(pro, days=400)
    clock.set(at(9, day=datetime.date(2030, 3, 10)))
    for _ in range(4):
        campaigns.send(campaign(pro, segment="all"))
    with pytest.raises(errors.CampaignLimit) as limit:
        campaigns.send(campaign(pro, segment="all"))
    assert limit.value.details == {"limit": 4}
