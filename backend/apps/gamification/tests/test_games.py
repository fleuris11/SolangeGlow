"""The games and what gives points elsewhere: quiz, « Help me choose », photo challenge,
rewards and vouchers on the France Selection, referrals, levels of the pros, rankings,
routine and the calendar of celebrations."""

import datetime
import uuid

import pytest
from django.utils import timezone

from apps.academy.models import Course, Enrollment
from apps.core.tests.factories import CountryFactory, CurrencyFactory, PlatformSettingFactory
from apps.gamification import errors
from apps.gamification.generators import AiGenerator, DraftQuestion, ManualGenerator
from apps.gamification.models import (
    Action,
    Celebration,
    Challenge,
    GlowProfile,
    PointsEntry,
    Poll,
    QuizDay,
    QuizQuestion,
    Ranking,
    Referral,
    Reward,
    RoutineStep,
    Voucher,
)
from apps.gamification.services import (
    celebrations,
    challenges,
    hooks,
    levels,
    points,
    polls,
    quiz,
    rankings,
    referrals,
    rewards,
    routine,
)
from apps.messaging.tests.factories import adult, minor
from apps.notifications.models import Notification
from apps.payments import services as payment_services
from apps.payments.models import Payment
from apps.pros.models import Level as ProLevel
from apps.pros.tests.factories import ProFactory, trade
from apps.selection_france.tests import factories as selection
from apps.social import services as social_services
from apps.social.models import Review
from apps.social.tests.factories import asset

pytestmark = pytest.mark.django_db
NOON = datetime.datetime(2026, 11, 2, 11, 0, tzinfo=datetime.UTC)
TODAY = datetime.date(2026, 11, 2)


def balance(user):
    return points.balance(user)


# --- Quiz ------------------------------------------------------------------------------------


def make_quiz(day=TODAY, count=3, approve=True, actor=None) -> QuizDay:
    found = QuizDay.objects.create(date=day)
    for n in range(count):
        QuizQuestion.objects.create(
            quiz=found,
            position=n,
            text=f"Question {n}",
            choice_1="Oui",
            choice_2="Non",
            choice_3="Peut-être",
            answer=2,
            explanation="Le karité nourrit.",
        )
    if approve:
        quiz.approve(found, actor=actor or adult("Equipe"))
    return found


def test_a_right_answer_gives_points_once():
    awa = adult()
    question = make_quiz().questions.first()
    found = quiz.answer(awa, question.pk, 2, now=NOON)
    assert found == {
        "correct": True,
        "answer": 2,
        "explanation": "Le karité nourrit.",
        "gained": 10,
    }
    with pytest.raises(errors.AlreadyAnswered):
        quiz.answer(awa, question.pk, 1, now=NOON)
    wrong = quiz.answer(awa, make_quiz_question_two(question), 1, now=NOON)
    assert (wrong["correct"], wrong["gained"]) == (False, 0)
    assert balance(awa) == 10


def make_quiz_question_two(question):
    return question.quiz.questions.exclude(pk=question.pk).first().pk


def test_only_todays_approved_quiz_and_its_choices():
    awa = adult()
    draft = make_quiz(day=TODAY + datetime.timedelta(days=1), approve=False)
    with pytest.raises(errors.QuestionNotFound):
        quiz.answer(awa, draft.questions.first().pk, 2, now=NOON)
    question = make_quiz().questions.first()
    with pytest.raises(errors.InvalidChoice):
        quiz.answer(awa, question.pk, 4, now=NOON)


def test_a_quiz_is_approved_only_when_complete():
    found = make_quiz(count=2, approve=False)
    with pytest.raises(errors.QuizIncomplete):
        quiz.approve(found, actor=adult("Equipe"))
    QuizQuestion.objects.create(
        quiz=found, position=3, text="", choice_1="a", choice_2="b", answer=1
    )
    with pytest.raises(errors.QuizIncomplete):
        quiz.approve(found, actor=adult("Equipe2"))


def test_drafts_are_prepared_ahead_by_the_generator(monkeypatch):
    assert quiz.prepare(now=NOON) == 7
    assert quiz.prepare(now=NOON) == 0
    assert set(QuizDay.objects.values_list("status", flat=True)) == {"draft"}
    assert not QuizQuestion.objects.exists()  # manual: the team writes them

    class Proposing(ManualGenerator):
        name = "ai"

        def questions(self, day, count, language):
            return [DraftQuestion("Le karité vient du ?", ["Bénin", "Canada"], 1, "Arbre")] * count

    monkeypatch.setattr("apps.gamification.services.quiz.generator", lambda: Proposing())
    later = NOON + datetime.timedelta(days=1)
    assert quiz.prepare(now=later) == 1
    proposed = QuizDay.objects.order_by("-date").first()
    assert proposed.generated_by == "ai"
    assert proposed.questions.count() == 3
    assert proposed.status == "draft"  # never online without the team


def test_the_ai_generator_is_off_without_keys(settings):
    from apps.core.providers import ProviderNotConfigured

    settings.QUIZ_AI_URL = ""
    with pytest.raises(ProviderNotConfigured):
        AiGenerator().questions(TODAY, 3, "fr")


# --- « Help me choose » ----------------------------------------------------------------------


def make_poll(author, hours=24) -> Poll:
    a, b = asset(author, purpose="poll_photo"), asset(author, purpose="poll_photo")
    return polls.create(
        author, caption="Robe rouge ou wax ?", photo_a=a.pk, photo_b=b.pk, hours=hours
    )


def test_a_poll_votes_and_the_result():
    awa, fifame, grace = adult(), adult("Fifamè"), adult("Grâce")
    poll = make_poll(awa)
    assert balance(awa) == 5
    polls.vote(fifame, poll, "a")
    found = polls.vote(grace, poll, "b")
    assert polls.result(found) == {"total": 2, "a": 50, "b": 50}
    assert balance(fifame) == 2
    with pytest.raises(errors.AlreadyVoted):
        polls.vote(fifame, poll, "b")
    with pytest.raises(errors.OwnPoll):
        polls.vote(awa, poll, "a")
    with pytest.raises(errors.InvalidChoice):
        polls.vote(adult("Lina"), poll, "c")


def test_a_poll_needs_two_own_photos_and_a_duration_offered():
    awa, other = adult(), adult("Fifamè")
    mine = asset(awa, purpose="poll_photo")
    with pytest.raises(errors.InvalidPhotos):
        polls.create(awa, caption="?", photo_a=mine.pk, photo_b=mine.pk, hours=24)
    with pytest.raises(errors.InvalidPhotos):
        theirs = asset(other, purpose="poll_photo")
        polls.create(awa, caption="?", photo_a=mine.pk, photo_b=theirs.pk, hours=24)
    with pytest.raises(errors.InvalidDuration):
        make_poll(awa, hours=5)


def test_open_polls_per_person_are_limited():
    awa = adult()
    for _ in range(3):
        make_poll(awa)
    with pytest.raises(errors.TooManyPolls):
        make_poll(awa)


def test_an_ended_poll_is_closed_and_its_author_told():
    awa, fifame = adult(), adult("Fifamè")
    poll = make_poll(awa, hours=1)
    later = timezone.now() + datetime.timedelta(hours=2)
    Poll.objects.filter(pk=poll.pk).update(ends_at=timezone.now() - datetime.timedelta(minutes=1))
    with pytest.raises(errors.PollClosed):
        polls.vote(fifame, poll, "a")
    assert polls.send_results(now=later) == 1
    assert polls.send_results(now=later) == 0
    assert Notification.objects.filter(user=awa, event_key="glow.poll_result").exists()


def test_polls_to_vote_skip_mine_and_voted_ones():
    awa, fifame = adult(), adult("Fifamè")
    poll = make_poll(awa)
    assert list(polls.to_vote(fifame)) == [poll]
    assert list(polls.to_vote(awa)) == []
    polls.vote(fifame, poll, "a")
    assert list(polls.to_vote(fifame)) == []


# --- Photo challenge -------------------------------------------------------------------------


def this_week(theme="Look pagne du dimanche") -> Challenge:
    monday = challenges.monday_of(timezone.localdate())
    found = Challenge.objects.create(
        theme=theme, starts_on=monday, ends_on=monday + datetime.timedelta(days=6)
    )
    return challenges.approve(found, actor=adult("Equipe"))


def test_a_challenge_entries_votes_and_winner():
    challenge = this_week()
    awa, fifame, grace = adult(), adult("Fifamè"), adult("Grâce")
    first = challenges.enter(awa, photo_id=asset(awa, purpose="challenge_photo").pk)
    second = challenges.enter(fifame, photo_id=asset(fifame, purpose="challenge_photo").pk)
    with pytest.raises(errors.AlreadyEntered):
        challenges.enter(awa, photo_id=asset(awa, purpose="challenge_photo").pk)
    challenges.vote(grace, second.pk)
    challenges.vote(awa, second.pk)
    challenges.vote(fifame, first.pk)
    with pytest.raises(errors.OwnEntry):
        challenges.vote(awa, first.pk)
    with pytest.raises(errors.AlreadyVoted):
        challenges.vote(grace, second.pk)
    Challenge.objects.filter(pk=challenge.pk).update(
        starts_on=challenge.starts_on - datetime.timedelta(days=7),
        ends_on=challenge.ends_on - datetime.timedelta(days=7),
    )
    assert challenges.close_due() == 1
    challenge.refresh_from_db()
    assert challenge.winner == second
    assert balance(fifame) == 15 + 2 + 300
    assert challenges.featured().pk == challenge.pk
    assert Notification.objects.filter(user=fifame, event_key="glow.challenge_won").exists()


def test_votes_per_challenge_are_limited():
    this_week()
    voter = adult("Grâce")
    entries = [
        challenges.enter(p, photo_id=asset(p, purpose="challenge_photo").pk)
        for p in (adult(f"P{n}") for n in range(4))
    ]
    for entry in entries[:3]:
        challenges.vote(voter, entry.pk)
    with pytest.raises(errors.NoVotesLeft):
        challenges.vote(voter, entries[3].pk)


def test_no_challenge_this_week_and_drafts_ahead():
    awa = adult()
    with pytest.raises(errors.NoChallenge):
        challenges.enter(awa, photo_id=asset(awa, purpose="challenge_photo").pk)
    assert challenges.prepare() == 4
    draft = Challenge.objects.order_by("starts_on").first()
    with pytest.raises(errors.ChallengeIncomplete):
        challenges.approve(draft, actor=awa)


# --- Rewards and vouchers --------------------------------------------------------------------


@pytest.fixture
def fenty():
    return selection.product()


def rich(user, amount=2000):
    points.adjust(user, amount, note="test", actor=None)


def test_a_reward_gives_a_voucher_used_on_the_france_selection(fenty):
    awa = adult()
    rich(awa)
    reward = Reward.objects.get(kind="amount_off", amount_off_minor=1000)
    found = rewards.redeem(awa, reward.pk)
    voucher = found["voucher"]
    assert balance(awa) == 1500
    order = selection.order(awa, fenty, voucher=voucher.code.lower(), paid=False)
    assert (order.discount_xof, order.total_xof) == (1000, 25_300 - 1000)
    assert order.payment.items_minor == 24_300
    voucher.refresh_from_db()
    assert voucher.used_for_id == order.pk
    with pytest.raises(errors.VoucherNotFound):
        selection.order(awa, fenty, voucher=voucher.code)
    # Not paid: the voucher comes back.
    payment_services.mark_not_paid(order.payment, reason="expired")
    voucher.refresh_from_db()
    assert voucher.used_at is None


def test_free_express_only_on_an_express_order(fenty):
    awa = adult()
    rich(awa)
    voucher = rewards.redeem(awa, Reward.objects.get(kind="express").pk)["voucher"]
    with pytest.raises(errors.VoucherNotForThis):
        selection.order(awa, fenty, voucher=voucher.code, paid=False)
    order = selection.order(awa, fenty, mode="express", voucher=voucher.code, paid=False)
    assert order.total_xof == 25_300  # the express price of the grouped one


def test_a_reward_needs_the_level_the_points_and_an_adult():
    awa = adult()
    star = Reward.objects.get(min_level="star")
    rich(awa, 400)
    with pytest.raises(errors.RewardLocked):
        rewards.redeem(awa, star.pk)
    with pytest.raises(errors.NotEnoughPoints):
        rewards.redeem(awa, Reward.objects.get(kind="express").pk)
    lina = minor()
    rich(lina)
    with pytest.raises(errors.CannotBuy):
        rewards.redeem(lina, Reward.objects.get(kind="amount_off", min_level="glow").pk)
    assert balance(lina) == 2000


def test_a_reward_sold_out_and_a_course_of_the_platform():
    awa = adult()
    rich(awa)
    reward = Reward.objects.get(kind="express")
    reward.stock = 1
    reward.save()
    rewards.redeem(awa, reward.pk)
    with pytest.raises(errors.RewardSoldOut):
        rewards.redeem(awa, reward.pk)
    course = Course.objects.create(
        slug="bases-du-maquillage",
        author=adult("Solange"),
        title="Les bases du maquillage",
        country=awa.country,
        pricing=Course.Pricing.PAID,
        price_minor=15_000,
        currency="XOF",
        status=Course.Status.PUBLISHED,
    )
    gift = Reward.objects.create(title="Formation", kind="course", cost_points=300, course=course)
    rewards.redeem(awa, gift.pk)
    enrolled = Enrollment.objects.get(user=awa, course=course)
    assert enrolled.access == Enrollment.Access.POINTS
    assert not Payment.objects.filter(buyer=awa, purpose="training").exists()


def test_a_voucher_keeps_the_least_to_pay(fenty):
    awa = adult()
    voucher = rewards.create_voucher(
        awa, kind=Voucher.Kind.AMOUNT_OFF, origin="wheel", amount_minor=50_000, days=3
    )
    order = selection.order(awa, fenty, voucher=voucher.code, paid=False)
    assert order.total_xof == 1000


# --- What gives points elsewhere -------------------------------------------------------------


def test_a_published_post_gives_points_through_the_events():
    awa = adult()
    social_services.create_post(awa, kind="photo", media=[{"id": asset(awa).pk}], caption="Tresses")
    assert PointsEntry.objects.filter(user=awa, action=Action.POST).count() == 1


def test_a_review_an_appointment_and_a_released_purchase(fenty):
    awa = adult()
    pro = ProFactory()
    review = Review.objects.create(
        author=awa, pro=pro, source_type="booking", source_id=uuid.uuid4(), rating=5
    )
    hooks.on_review_created(review)

    class Done:
        pk = uuid.uuid4()
        client_id = awa.pk
        client = awa

    hooks.on_appointment_completed(Done())
    order = selection.order(awa, fenty)
    payment_services.release(order.payment, reason="test")
    actions = set(PointsEntry.objects.filter(user=awa).values_list("action", flat=True))
    assert actions == {Action.REVIEW, Action.BOOKING, Action.PURCHASE}
    assert balance(awa) == 20 + 30 + 30


# --- Referrals -------------------------------------------------------------------------------


def test_referral_points_after_the_first_purchase_only(fenty):
    awa, fifame = adult(), adult("Fifamè")
    code = GlowProfile.objects.get_or_create(user=awa, defaults={"referral_code": "AWA12345"})[0]
    referrals.attach(fifame, code.referral_code.lower())
    with pytest.raises(errors.AlreadyReferred):
        referrals.attach(fifame, code.referral_code)
    order = selection.order(fifame, fenty)
    assert balance(awa) == 0  # paid, not released yet
    payment_services.release(order.payment, reason="test")
    assert (balance(awa), balance(fifame)) == (200, 100 + 30)
    second = selection.order(fifame, fenty)
    payment_services.release(second.payment, reason="test")
    assert balance(awa) == 200


def test_referral_refusals():
    awa = adult()
    code = GlowProfile.objects.create(user=awa, referral_code="AWA12345").referral_code
    with pytest.raises(errors.OwnReferral):
        referrals.attach(awa, code)
    with pytest.raises(errors.InvalidReferral):
        referrals.attach(adult("Fifamè"), "NOPE")
    old = adult("Grâce")
    type(old).objects.filter(pk=old.pk).update(
        created_at=timezone.now() - datetime.timedelta(days=30)
    )
    old.refresh_from_db()
    with pytest.raises(errors.ReferralTooLate):
        referrals.attach(old, code)


def test_the_godmother_monthly_limit(fenty):
    PlatformSettingFactory(key="glow.referral_monthly_max", value="1")
    awa = adult()
    code = GlowProfile.objects.create(user=awa, referral_code="AWA12345").referral_code
    for name in ("Fifamè", "Grâce"):
        friend = adult(name)
        referrals.attach(friend, code)
        payment_services.release(selection.order(friend, fenty).payment, reason="test")
    assert balance(awa) == 200
    assert Referral.objects.filter(referrer=awa, capped=True).count() == 1


# --- Pros: levels and rankings ---------------------------------------------------------------


def reviews(pro, ratings, *, when=None):
    for rating in ratings:
        review = Review.objects.create(
            author=adult(f"C{uuid.uuid4().hex[:4]}"),
            pro=pro,
            source_type="booking",
            source_id=uuid.uuid4(),
            rating=rating,
        )
        if when:
            Review.objects.filter(pk=review.pk).update(created_at=when)


def test_levels_of_the_pros(monkeypatch):
    pro = ProFactory()
    assert levels.refresh(pro) == ProLevel.NEW
    reviews(pro, [5, 5, 4, 5, 4])
    monkeypatch.setattr(
        levels, "stats", lambda p: {"done": 12, "reviews": 5, "average": 4.6, "verified": False}
    )
    assert levels.refresh(pro) == ProLevel.CONFIRMED
    pro.refresh_from_db()
    assert pro.level == ProLevel.CONFIRMED
    assert Notification.objects.filter(user=pro.user, event_key="glow.pro_level_up").exists()
    monkeypatch.setattr(
        levels, "stats", lambda p: {"done": 80, "reviews": 30, "average": 4.8, "verified": False}
    )
    assert levels.level_of(pro) == ProLevel.CONFIRMED  # Top pro must be verified


def test_monthly_rankings_per_city_and_trade_on_verified_reviews():
    month = datetime.date(2026, 10, 1)
    inside = timezone.make_aware(datetime.datetime(2026, 10, 15, 12))
    star = ProFactory(city="Cotonou", trades=["braids"])
    many = ProFactory(city="Cotonou", trades=["braids"])
    few = ProFactory(city="Cotonou", trades=["braids"])
    reviews(star, [5, 4, 5], when=inside)
    reviews(many, [5] * 10, when=inside)
    reviews(few, [5, 5], when=inside)  # under the minimum
    reviews(star, [1, 1, 1], when=inside + datetime.timedelta(days=30))  # next month
    assert rankings.compute(month) == 2
    rows = list(rankings.table(month=month, city="cotonou", trade_id=trade("braids").pk))
    assert [r.pro for r in rows] == [many, star]
    assert rows[0].position == 1
    assert rankings.ensure_last_month(now=timezone.make_aware(datetime.datetime(2026, 11, 2))) == 0
    Ranking.objects.all().delete()
    assert rankings.ensure_last_month(now=timezone.make_aware(datetime.datetime(2026, 11, 2))) == 2


# --- Routine and calendar --------------------------------------------------------------------


def test_routine_ticked_gives_points_once_the_moment_is_done():
    awa = adult()
    routine.save_steps(awa, morning=["Nettoyer", "Hydrater"], evening=["Démaquiller"])
    steps = list(RoutineStep.objects.filter(user=awa, moment="morning"))
    routine.check(awa, steps[0].pk, done=True, now=NOON)
    assert balance(awa) == 0
    state = routine.check(awa, steps[1].pk, done=True, now=NOON)
    assert [s["done"] for s in state["morning"]] == [True, True]
    assert balance(awa) == 3
    routine.check(awa, steps[1].pk, done=False, now=NOON)
    routine.check(awa, steps[1].pk, done=True, now=NOON)
    assert balance(awa) == 3
    with pytest.raises(errors.StepNotFound):
        routine.check(adult("Fifamè"), steps[0].pk, done=True)
    with pytest.raises(errors.TooManySteps):
        routine.save_steps(awa, morning=["x"] * 9, evening=[])


def test_routine_reminder_at_the_chosen_hour():
    awa = adult()  # Cotonou, UTC+1
    routine.save_steps(awa, morning=["Nettoyer"], evening=[])
    routine.set_reminders(
        awa,
        routine_reminders=True,
        morning_at=datetime.time(7, 30),
        evening_at=datetime.time(21, 0),
        celebration_reminders=True,
    )
    before = datetime.datetime(2026, 11, 2, 6, 0, tzinfo=datetime.UTC)  # 7:00 there
    assert routine.send_reminders(now=before) == 0
    at = datetime.datetime(2026, 11, 2, 6, 40, tzinfo=datetime.UTC)  # 7:40 there
    assert routine.send_reminders(now=at) == 1
    assert routine.send_reminders(now=at) == 0
    assert Notification.objects.filter(user=awa, event_key="glow.routine_reminder").count() == 1


def test_celebrations_coming_and_their_reminder():
    Celebration.objects.all().delete()
    yearly = Celebration.objects.create(name="Noël", date=datetime.date(2020, 12, 25), yearly=True)
    once = Celebration.objects.create(
        name="Tabaski", date=datetime.date(2027, 5, 16), countries=["BJ"], remind_days=10
    )
    Celebration.objects.create(name="Passée", date=datetime.date(2025, 1, 1))
    found = celebrations.upcoming("BJ", TODAY)
    assert [(c.name, d) for c, d in found] == [
        ("Noël", datetime.date(2026, 12, 25)),
        ("Tabaski", datetime.date(2027, 5, 16)),
    ]
    assert [c for c, _ in celebrations.upcoming("FR", TODAY)] == [yearly]
    awa = adult(onboarded_at=timezone.now())
    off = adult("Fifamè", onboarded_at=timezone.now())
    GlowProfile.objects.create(user=off, referral_code="OFF12345", celebration_reminders=False)
    day = timezone.make_aware(datetime.datetime(2027, 5, 6, 8))
    assert celebrations.send_reminders(now=day) == 1
    assert celebrations.send_reminders(now=day) == 0
    assert Notification.objects.filter(user=awa, event_key="glow.celebration").exists()
    assert once.pk


def test_france_and_benin_days():
    france = CountryFactory(
        code="FR",
        name="France",
        phone_prefix="+33",
        timezone="Europe/Paris",
        default_currency=CurrencyFactory(code="EUR", name="Euro", symbol="€", decimal_places=2),
    )
    grace = adult("Grâce", country=france)
    late = datetime.datetime(2026, 11, 2, 23, 30, tzinfo=datetime.UTC)
    entry = points.award(grace, Action.REVIEW, key="late", now=late)
    assert entry.day == datetime.date(2026, 11, 3)
