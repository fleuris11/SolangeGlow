"""Glow Points: the scale per action, the anti-abuse caps, the levels, the append-only
ledger, spending, the team's corrections and the visit streak."""

import datetime

import pytest
from django.db import DatabaseError, transaction

from apps.core.models import FeatureFlag, PlatformSetting
from apps.core.tests.factories import PlatformSettingFactory
from apps.gamification import errors
from apps.gamification.models import Action, GlowProfile, Level, PointsEntry
from apps.gamification.services import points, streaks
from apps.messaging.tests.factories import adult
from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db
JSON = PlatformSetting.ValueType.JSON
INT = PlatformSetting.ValueType.INTEGER
NOON = datetime.datetime(2026, 11, 2, 11, 0, tzinfo=datetime.UTC)  # a Monday, noon in Cotonou


def setting(key, value, value_type=JSON):
    PlatformSettingFactory(key=key, value=value, value_type=value_type)


def test_each_action_gives_the_points_of_the_scale():
    awa = adult()
    entry = points.award(awa, Action.REVIEW, key="review:1")
    assert entry.amount == 20
    setting("glow.points", '{"review": 35}')
    assert points.award(awa, Action.REVIEW, key="review:2").amount == 35
    assert points.balance(awa) == 55
    assert GlowProfile.objects.get(user=awa).earned_total == 55


def test_an_event_replayed_gives_nothing_more():
    awa = adult()
    assert points.award(awa, Action.POST, key="post:42") is not None
    assert points.award(awa, Action.POST, key="post:42") is None
    assert PointsEntry.objects.filter(user=awa).count() == 1


def test_an_action_out_of_the_scale_or_at_zero_gives_nothing():
    awa = adult()
    setting("glow.points", '{"poll_vote": 0}')
    assert points.award(awa, Action.POLL_VOTE, key="v:1") is None
    assert points.award(awa, Action.REWARD, key="r:1") is None


def test_the_daily_cap_of_an_action():
    awa = adult()
    setting("glow.daily_caps", '{"post": 2}')
    given = [points.award(awa, Action.POST, key=f"post:{n}", now=NOON) for n in range(4)]
    assert [bool(g) for g in given] == [True, True, False, False]
    # The next day counts again.
    tomorrow = NOON + datetime.timedelta(days=1)
    assert points.award(awa, Action.POST, key="post:9", now=tomorrow) is not None


def test_the_daily_ceiling_trims_the_last_gain_and_spares_the_bonuses():
    awa = adult()
    setting("glow.daily_max_points", "45", INT)
    setting("glow.daily_caps", "{}")
    first = points.award(awa, Action.REVIEW, key="a", now=NOON)
    second = points.award(awa, Action.REVIEW, key="b", now=NOON)
    third = points.award(awa, Action.REVIEW, key="c", now=NOON)
    assert (first.amount, second.amount, third.amount) == (20, 20, 5)
    assert points.award(awa, Action.REVIEW, key="d", now=NOON) is None
    assert points.earned_on(awa, NOON.date())["ceiling"] == 45
    # A bonus (streak, referral, challenge won, wheel) is outside the ceiling.
    assert points.award(awa, Action.CHALLENGE_WIN, key="win", now=NOON).amount == 300


def test_the_ceiling_counts_in_the_day_of_her_country():
    awa = adult()  # Benin, UTC+1
    late = datetime.datetime(2026, 11, 2, 23, 30, tzinfo=datetime.UTC)  # already 3 Nov there
    entry = points.award(awa, Action.REVIEW, key="late", now=late)
    assert entry.day == datetime.date(2026, 11, 3)


def test_the_games_closed_in_her_country_give_nothing():
    awa = adult()
    FeatureFlag.objects.filter(key="games").update(is_enabled=False)
    assert points.award(awa, Action.REVIEW, key="closed") is None
    with pytest.raises(errors.GamesUnavailable):
        streaks.check_in(awa)


def test_levels_rise_with_the_points_earned_and_multiply_the_gains():
    awa = adult()
    setting("glow.level_thresholds", '{"star": 100, "icon": 400}')
    setting("glow.daily_caps", "{}")
    setting("glow.daily_max_points", "100000", INT)
    for n in range(5):
        points.award(awa, Action.REVIEW, key=f"r{n}")
    profile = GlowProfile.objects.get(user=awa)
    assert profile.level == Level.STAR
    assert Notification.objects.filter(user=awa, event_key="glow.level_up").count() == 1
    # Star: x 1.1, rounded down.
    assert points.award(awa, Action.REVIEW, key="star").amount == 22
    assert points.next_level(profile.earned_total) == (Level.ICON, 400)


def test_spending_never_goes_below_zero():
    awa = adult()
    points.award(awa, Action.BOOKING, key="b1")
    with transaction.atomic():
        spent = points.spend(awa, 20, key="reward:1")
    assert spent.amount == -20
    assert points.balance(awa) == 10
    with pytest.raises(errors.NotEnoughPoints):
        points.spend(awa, 11, key="reward:2")
    # Spending does not lower the level.
    assert GlowProfile.objects.get(user=awa).earned_total == 30


def test_the_ledger_cannot_be_changed_or_deleted():
    awa = adult()
    entry = points.award(awa, Action.BOOKING, key="b1")
    with pytest.raises(DatabaseError), transaction.atomic():
        PointsEntry.objects.filter(pk=entry.pk).update(amount=999)
    with pytest.raises(DatabaseError), transaction.atomic():
        PointsEntry.objects.filter(pk=entry.pk).delete()


def test_the_team_gives_or_takes_back_points_in_the_journal():
    awa, team = adult(), adult("Equipe")
    points.adjust(awa, 50, note="Concours Instagram", actor=team)
    points.adjust(awa, -20, note="Fraude", actor=team)
    assert points.balance(awa) == 30
    with pytest.raises(errors.NotEnoughPoints):
        points.adjust(awa, -31, note="Trop", actor=team)
    assert PointsEntry.objects.filter(user=awa, action=Action.ADJUSTMENT).count() == 2


# --- Streak ----------------------------------------------------------------------------------


def test_a_visit_a_day_and_the_bonus_after_seven_days():
    awa = adult()
    results = [streaks.check_in(awa, now=NOON + datetime.timedelta(days=d)) for d in range(7)]
    assert [r["streak"] for r in results] == [1, 2, 3, 4, 5, 6, 7]
    assert [r["bonus"] for r in results] == [0, 0, 0, 0, 0, 0, 50]
    assert all(r["gained"] == 5 for r in results)
    assert points.balance(awa) == 7 * 5 + 50


def test_two_visits_the_same_day_count_once():
    awa = adult()
    first = streaks.check_in(awa, now=NOON)
    again = streaks.check_in(awa, now=NOON + datetime.timedelta(hours=3))
    assert (first["already"], again["already"]) == (False, True)
    assert again["gained"] == 0
    assert points.balance(awa) == 5


def test_the_flame_goes_out_when_a_day_is_missed():
    awa = adult()
    streaks.check_in(awa, now=NOON)
    streaks.check_in(awa, now=NOON + datetime.timedelta(days=1))
    two_days_later = NOON + datetime.timedelta(days=3)
    assert streaks.state(awa, now=two_days_later)["streak"] == 0
    after = streaks.check_in(awa, now=two_days_later)
    assert after["streak"] == 1
    assert after["best"] == 2
    assert after["to_bonus"] == 6


def test_the_profile_gets_a_personal_referral_code():
    awa, fifame = adult(), adult("Fifamè")
    points.summary(awa)
    points.summary(fifame)
    codes = set(GlowProfile.objects.values_list("referral_code", flat=True))
    assert len(codes) == 2
    assert all(len(code) == 8 for code in codes)
