"""Ads: targeting, repeats per person and per day, ceiling per screen, sold campaigns
before house promotions, minors, impressions counted when shown, clicks, conversions,
end of the campaigns, boosts paid by the pros."""

import datetime
import random

import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.ads import errors
from apps.ads.models import AdClick, AdStat, Advertiser, Boost, Campaign, Creative
from apps.ads.services import boosts, campaigns, common, delivery, hooks, tracking
from apps.core.models import FeatureFlag, PlatformSetting
from apps.core.tests.factories import PlatformSettingFactory
from apps.messaging.tests.factories import adult, minor
from apps.notifications.models import Notification
from apps.payments import services as payment_services
from apps.payments.models import Payment
from apps.pros.tests.factories import ProFactory

pytestmark = pytest.mark.django_db
NOW = timezone.now()


def brand(name="Karité Doux") -> Advertiser:
    return Advertiser.objects.create(name=name)


def campaign(*, kind=Campaign.Kind.SOLD, placements=("home_banner",), status="active", **values):
    found = Campaign.objects.create(
        advertiser=values.pop("advertiser", None) or brand(),
        name=values.pop("name", "Rentrée"),
        kind=kind,
        status=status,
        starts_at=values.pop("starts_at", NOW - datetime.timedelta(days=1)),
        ends_at=values.pop("ends_at", NOW + datetime.timedelta(days=7)),
        **values,
    )
    Creative.objects.create(
        campaign=found,
        name="Visuel",
        format=Creative.Format.IMAGE,
        placements=list(placements),
        title="Le karité qui nourrit",
        link="/selection",
    )
    common.changed()
    return found


def audience(user=None, **values):
    return common.audience_of(user, visitor=values.pop("visitor", "visitor-1"), **values)


def pick(placement="home_banner", who=None, **kwargs):
    return delivery.pick(placement, who or audience(country="BJ"), **kwargs)


def test_a_running_campaign_is_shown_and_counted():
    sold = campaign()
    shown = pick()
    assert [c.campaign_id for c in shown] == [sold.pk]
    stat = AdStat.objects.get(campaign=sold)
    assert (stat.impressions, stat.placement) == (1, "home_banner")


def test_dates_status_and_placement():
    campaign(starts_at=NOW + datetime.timedelta(days=1), name="Plus tard")
    campaign(status="paused", name="En pause")
    campaign(placements=("feed",), name="Fil")
    assert pick() == []
    assert len(pick("feed")) == 1
    assert pick("unknown") == []


def test_targeting_country_city_language_role_trade():
    campaign(
        countries=["BJ"], cities=["Cotonou"], languages=["fr"], roles=["pro"], trades=["braids"]
    )
    pro = ProFactory(user=adult("Aïcha", city="Cotonou"), city="Cotonou", trades=["braids"])
    assert len(pick(who=common.audience_of(pro.user))) == 1
    assert pick(who=audience(country="BJ", city="Cotonou")) == []  # a client, not a pro
    other = ProFactory(
        user=adult("Prisca", city="Porto-Novo"), city="Porto-Novo", trades=["braids"]
    )
    assert pick(who=common.audience_of(other.user)) == []


def test_repeats_per_person_and_per_day():
    campaign(max_per_day=2)
    me = audience(visitor="awa")
    assert len(pick(who=me)) == 1
    assert len(pick(who=me)) == 1
    assert pick(who=me) == []
    assert len(pick(who=audience(visitor="fifame"))) == 1
    tomorrow = timezone.now() + datetime.timedelta(days=1)
    assert len(pick(who=me, now=tomorrow)) == 1


def test_ceiling_per_screen_and_one_creative_per_campaign():
    for n in range(4):
        campaign(placements=("feed",), name=f"C{n}")
    assert len(pick("feed", count=10)) == 2  # ads.max_per_screen: 2 in the feed
    PlatformSettingFactory(
        key="ads.max_per_screen", value='{"feed": 3}', value_type=PlatformSetting.ValueType.JSON
    )
    cache.clear()
    found = pick("feed", count=10, who=audience(visitor="other"))
    assert len(found) == 3
    assert len({c.campaign_id for c in found}) == 3


def test_house_promotions_only_when_nothing_is_sold():
    house = campaign(kind=Campaign.Kind.HOUSE, name="Offrir au pays")
    assert [c.campaign_id for c in pick()] == [house.pk]
    sold = campaign(name="Vendue")
    assert [c.campaign_id for c in pick(who=audience(visitor="b"))] == [sold.pk]


def test_priority_weights_the_draw():
    high = campaign(priority=9, name="Haute", placements=("search",))
    campaign(priority=1, name="Basse", placements=("search",))
    rng = random.Random(7)  # noqa: S311 - a seeded draw, not for security
    wins = sum(
        pick("search", who=audience(visitor=f"v{n}"), rng=rng)[0].campaign_id == high.pk
        for n in range(300)
    )
    assert 240 < wins < 295  # 90 % expected


def test_no_ads_for_minors_nor_where_ads_are_off():
    campaign()
    assert pick(who=common.audience_of(minor())) == []
    assert len(pick(who=common.audience_of(adult()))) == 1
    FeatureFlag.objects.filter(key="ads").update(is_enabled=False)
    cache.clear()
    assert pick(who=audience(visitor="z")) == []


def test_impressions_bought_stop_the_campaign():
    sold = campaign(impressions_bought=2, max_per_day=10)
    assert len(pick(who=audience(visitor="a"))) == 1
    assert len(pick(who=audience(visitor="b"))) == 1
    assert pick(who=audience(visitor="c")) == []
    assert campaigns.end_due() == 1
    sold.refresh_from_db()
    assert sold.status == Campaign.Status.ENDED


def test_a_click_counts_and_leads_to_the_page():
    sold = campaign()
    creative = sold.creatives.get()
    token = tracking.click_token(creative, "home_banner")
    assert tracking.click(token, adult()) == "/selection"
    assert AdStat.objects.get(creative=creative).clicks == 1
    with pytest.raises(errors.AdNotFound):
        tracking.click(token + "x")


def test_unsafe_links_are_refused():
    assert tracking.safe_link("/aicha")
    assert tracking.safe_link("https://karite.bj")
    assert not tracking.safe_link("//evil.example")
    assert not tracking.safe_link("javascript:alert(1)")
    assert not tracking.safe_link("http://karite.bj")


def test_a_purchase_after_a_click_is_a_conversion_once():
    awa = adult()
    sold = campaign()
    creative = sold.creatives.get()
    tracking.click(tracking.click_token(creative, "home_banner"), awa)
    assert tracking.convert(awa, "payment:1") is True
    assert tracking.convert(awa, "payment:2") is False
    assert AdStat.objects.get(creative=creative).conversions == 1
    late = adult("Fifamè")
    tracking.click(tracking.click_token(creative, "home_banner"), late)
    AdClick.objects.filter(user=late).update(created_at=timezone.now() - datetime.timedelta(days=8))
    assert tracking.convert(late, "payment:3") is False


def test_boost_payments_are_never_conversions():
    awa = adult()
    sold = campaign()
    tracking.click(tracking.click_token(sold.creatives.get(), "home_banner"), awa)

    class Boosted:
        status = Payment.Status.HELD
        purpose = "boost"
        buyer = awa
        pk = 1

    hooks.on_payment_moved(Boosted())
    assert AdClick.objects.get(user=awa).converted_at is None


def test_campaign_check_before_it_runs():
    draft = campaign(status="draft", placements=())
    with pytest.raises(errors.InvalidCampaign):
        campaigns.activate(draft, actor=None)
    draft.creatives.update(placements=["feed"])
    campaigns.activate(draft, actor=None)
    draft.refresh_from_db()
    assert draft.status == Campaign.Status.ACTIVE
    campaigns.pause(draft, actor=None)
    draft.refresh_from_db()
    assert draft.status == Campaign.Status.PAUSED


# --- Boosts ------------------------------------------------------------------------------------


def paid(boost: Boost) -> Boost:
    payment = Payment.objects.get(pk=boost.payment_id)
    payment_services.mark_paid(
        payment, amount_minor=payment.total_minor, currency=payment.currency, key=f"t:{payment.pk}"
    )
    boost.refresh_from_db()
    return boost


def test_a_boost_is_paid_then_shown_first_in_her_city_and_trade():
    pro = ProFactory(user=adult("Aïcha"), city="Cotonou", trades=["braids"])
    boost = boosts.buy(pro, "day", actor=pro.user)
    payment = Payment.objects.get(pk=boost.payment_id)
    assert (payment.items_minor, payment.currency, payment.purpose) == (1000, "XOF", "boost")
    assert boost.status == Boost.Status.WAITING_PAYMENT
    boost = paid(boost)
    payment.refresh_from_db()
    assert payment.status == Payment.Status.RELEASED
    assert boost.status == Boost.Status.ACTIVE
    assert boost.ends_at - boost.starts_at == datetime.timedelta(days=1)
    campaign_ = boost.campaign
    assert (campaign_.kind, campaign_.cities, campaign_.trades) == (
        "boost",
        ["Cotonou"],
        ["braids"],
    )
    assert Notification.objects.filter(user=pro.user, event_key="ads.boost_started").exists()
    shown = pick("search", who=audience(country="BJ", city="Cotonou"), context={"trade": "braids"})
    assert shown and shown[0].pro_id == pro.pk
    assert (
        pick("search", who=audience(country="BJ", city="Cotonou"), context={"trade": "nails"}) == []
    )
    with pytest.raises(errors.BoostRunning):
        boosts.buy(pro, "week", actor=pro.user)


def test_a_boost_ends_with_its_figures():
    pro = ProFactory(user=adult("Aïcha"), city="Cotonou", trades=["braids"])
    boost = paid(boosts.buy(pro, "week", actor=pro.user))
    later = timezone.now() + datetime.timedelta(days=8)
    assert boosts.end_due(now=later) == 1
    boost.refresh_from_db()
    assert boost.status == Boost.Status.ENDED
    assert Notification.objects.filter(user=pro.user, event_key="ads.boost_ended").exists()
    assert campaigns.end_due(now=later) >= 1


def test_boost_refusals():
    with pytest.raises(errors.NotAPro):
        boosts.buy(ProFactory(user=adult("Draft"), status="draft"), "day", actor=None)
    pro = ProFactory(user=adult("Aïcha"))
    with pytest.raises(errors.NoBoostPrice):
        boosts.buy(pro, "month", actor=None)
    FeatureFlag.objects.filter(key="boosts").update(is_enabled=False)
    cache.clear()
    with pytest.raises(errors.BoostsUnavailable):
        boosts.buy(pro, "day", actor=None)


def test_an_unpaid_boost_is_cancelled():
    pro = ProFactory(user=adult("Aïcha"))
    boost = boosts.buy(pro, "day", actor=pro.user)
    payment_services.mark_not_paid(Payment.objects.get(pk=boost.payment_id), reason="expired")
    boost.refresh_from_db()
    assert boost.status == Boost.Status.CANCELLED
