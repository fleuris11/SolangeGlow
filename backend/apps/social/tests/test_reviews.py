import uuid
from decimal import Decimal

import pytest
from django.contrib.contenttypes.models import ContentType

from apps.core.tests.factories import PlatformSettingFactory
from apps.moderation import services as moderation
from apps.moderation.models import ModerationCase
from apps.notifications.models import Notification
from apps.pros.tests.factories import ProFactory
from apps.social import errors, selectors, services

from .factories import asset, person

pytestmark = pytest.mark.django_db


@pytest.fixture
def pro():
    return ProFactory(rating_average=None, rating_count=0)


def review(client, transaction, rating=5, **kwargs):
    return services.create_review(
        client, kind="booking", transaction_id=transaction.id, rating=rating, **kwargs
    )


def test_only_a_finished_booking_of_the_client_opens_a_review(bookings, pro):
    awa, ines = person(name="Awa"), person(name="Inès")
    done = bookings.add(awa, pro)
    not_done = bookings.add(awa, pro, finished=False)
    old = bookings.add(awa, pro, finished_days_ago=45)

    with pytest.raises(errors.TransactionNotFound):
        services.check_review_eligibility(awa, "booking", uuid.uuid4())
    with pytest.raises(errors.TransactionNotFound):
        services.check_review_eligibility(awa, "order", done.id)  # no shop yet
    with pytest.raises(errors.NotYourTransaction):
        services.check_review_eligibility(ines, "booking", done.id)
    with pytest.raises(errors.NotFinished):
        services.check_review_eligibility(awa, "booking", not_done.id)
    with pytest.raises(errors.TooLate):
        services.check_review_eligibility(awa, "booking", old.id)
    assert services.check_review_eligibility(awa, "booking", done.id) == done

    review(awa, done)
    with pytest.raises(errors.AlreadyReviewed):
        review(awa, done)


def test_the_review_window_is_a_setting(bookings, pro):
    awa = person()
    old = bookings.add(awa, pro, finished_days_ago=45)
    PlatformSettingFactory(key="reviews.window_days", value="60")
    assert services.check_review_eligibility(awa, "booking", old.id) == old


def test_a_pro_cannot_review_herself(bookings, pro):
    own = bookings.add(pro.user, pro)
    with pytest.raises(errors.NotYourTransaction):
        services.check_review_eligibility(pro.user, "booking", own.id)


def test_review_with_photo_and_voice_updates_the_average(bookings, pro):
    awa, ines = person(name="Awa"), person(name="Inès")
    first = review(
        awa,
        bookings.add(awa, pro),
        rating=5,
        text="Tresses parfaites",
        photo_id=asset(awa, purpose="review_photo").pk,
        voice_id=asset(awa, kind="audio", purpose="review_voice").pk,
    )
    review(ines, bookings.add(ines, pro), rating=4)
    pro.refresh_from_db()
    assert (pro.rating_average, pro.rating_count) == (Decimal("4.50"), 2)
    assert first.photo is not None and first.voice is not None
    assert Notification.objects.filter(user=pro.user, event_key="reviews.received").count() == 2

    case = ModerationCase.objects.create(
        target_type=ContentType.objects.get_for_model(first), target_id=first.pk, source="report"
    )
    moderation.decide(case, actor=None, keep=False)
    pro.refresh_from_db()
    assert (pro.rating_average, pro.rating_count) == (Decimal("4.00"), 1)


def test_the_pro_replies_once(bookings, pro):
    awa = person()
    item = review(awa, bookings.add(awa, pro), rating=3, text="Un peu de retard")
    with pytest.raises(errors.NotYours):
        services.reply_to_review(item, awa, "Moi aussi")
    services.reply_to_review(item, pro.user, "Désolée, merci pour ta patience.")
    assert item.replied_at is not None
    assert Notification.objects.filter(user=awa, event_key="reviews.replied").exists()
    with pytest.raises(errors.AlreadyReplied):
        services.reply_to_review(item, pro.user, "Encore")


def test_pending_reviews_list(bookings, pro):
    awa = person()
    done = bookings.add(awa, pro)
    bookings.add(awa, pro, finished=False)
    bookings.add(awa, pro, finished_days_ago=90)
    assert services.pending_reviews(awa) == [done]
    review(awa, done)
    assert services.pending_reviews(awa) == []


def test_pro_rates_her_client_privately(bookings, pro):
    awa = person()
    done = bookings.add(awa, pro)
    missed = bookings.add(awa, pro, finished=False)
    services.rate_client(pro, kind="booking", transaction_id=done.id, rating=5)
    services.rate_client(pro, kind="booking", transaction_id=missed.id, rating=1, no_show=True)
    assert selectors.client_reliability(awa) == {"average": 3.0, "count": 2, "no_shows": 1}
    other_pro = ProFactory()
    with pytest.raises(errors.NotYourTransaction):
        services.rate_client(other_pro, kind="booking", transaction_id=done.id, rating=1)


def test_without_booking_or_shop_nobody_can_review(pro):
    with pytest.raises(errors.TransactionNotFound):
        services.check_review_eligibility(person(), "booking", uuid.uuid4())
    assert services.pending_reviews(person(name="B")) == []
