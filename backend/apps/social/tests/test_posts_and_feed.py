import datetime

import pytest
from django.contrib.gis.geos import Point
from django.utils import timezone

from apps.core.tests.factories import CountryFactory, CurrencyFactory, PlatformSettingFactory
from apps.moderation import services as moderation
from apps.moderation.models import ModerationCase
from apps.notifications.models import Notification
from apps.pros.tests.factories import ProFactory, add_service
from apps.social import errors, services
from apps.social.feed import Cursor, feed
from apps.social.models import Follow, Post, Visibility

from .factories import asset, person, published_post

pytestmark = pytest.mark.django_db


# --- Creating posts ----------------------------------------------------------------------


def test_a_pro_posts_a_look_linked_to_her_service():
    pro = ProFactory(city="Abomey-Calavi")
    service = add_service(pro)
    picture = asset(pro.user)
    post = services.create_post(
        pro.user,
        kind="photo",
        media=[{"id": picture.pk}],
        caption="Knotless mi-dos",
        service_id=service.pk,
    )
    assert post.status == Post.Status.PUBLISHED and post.published_at is not None
    assert post.pro == pro and post.city == "Abomey-Calavi" and post.location == pro.location
    assert post.trade == service.trade
    assert post.is_live


def test_media_rules_per_kind():
    author = person()
    one, two = asset(author), asset(author)
    with pytest.raises(errors.InvalidMedia):
        services.create_post(author, kind="carousel", media=[{"id": one.pk}])
    with pytest.raises(errors.InvalidMedia):
        services.create_post(author, kind="video", media=[{"id": one.pk}])
    with pytest.raises(errors.InvalidMedia):
        services.create_post(
            author, kind="before_after", media=[{"id": one.pk, "role": "before"}, {"id": two.pk}]
        )
    pair = services.create_post(
        author,
        kind="before_after",
        media=[{"id": one.pk, "role": "before"}, {"id": two.pk, "role": "after"}],
    )
    assert [m.role for m in pair.media_items.all()] == ["before", "after"]
    with pytest.raises(errors.EmptyPost):
        services.create_post(author, kind="photo", media=[])


def test_someone_else_media_or_service_is_refused():
    author, other = person(), person(name="Gloria")
    with pytest.raises(errors.InvalidMedia):
        services.create_post(author, kind="photo", media=[{"id": asset(other).pk}])
    pro = ProFactory()
    with pytest.raises(errors.InvalidLink):
        services.create_post(
            author,
            kind="photo",
            media=[{"id": asset(author).pk}],
            service_id=add_service(pro).pk,
        )


def test_schedule_then_publish_when_due():
    author = person()
    with pytest.raises(errors.InvalidSchedule):
        services.create_post(
            author,
            kind="photo",
            media=[{"id": asset(author).pk}],
            status="scheduled",
            publish_at=timezone.now() - datetime.timedelta(minutes=5),
        )
    post = services.create_post(
        author,
        kind="photo",
        media=[{"id": asset(author).pk}],
        status="scheduled",
        publish_at=timezone.now() + datetime.timedelta(hours=2),
    )
    assert not post.is_live
    assert services.publish_due_posts() == 0
    Post.objects.filter(pk=post.pk).update(
        publish_at=timezone.now() - datetime.timedelta(seconds=1)
    )
    assert services.publish_due_posts() == 1
    post.refresh_from_db()
    assert post.is_live
    assert Notification.objects.filter(user=author, event_key="social.post_published").exists()


def test_draft_is_kept_aside_and_can_be_published_later():
    author = person()
    draft = services.create_post(
        author, kind="photo", media=[{"id": asset(author).pk}], status="draft"
    )
    assert draft.status == Post.Status.DRAFT
    services.update_post(draft, author, status="published", caption="Enfin prêt")
    assert draft.is_live and draft.caption == "Enfin prêt"
    with pytest.raises(errors.NotYours):
        services.update_post(draft, person(name="Inès"), caption="hack")


def test_forbidden_words_hold_the_post_and_open_a_case():
    PlatformSettingFactory(key="moderation.blocked_words", value_type="json", value='["salope"]')
    author = person()
    post = services.create_post(
        author, kind="photo", media=[{"id": asset(author).pk}], caption="Quelle salope !"
    )
    assert post.visibility == Visibility.HELD and not post.is_live
    case = ModerationCase.objects.get(target_id=post.pk)
    assert case.labels == ["blocked_word"] and case.hidden_until_review


def test_a_phone_number_is_queued_but_stays_visible():
    author = person()
    post = services.create_post(
        author, kind="photo", media=[{"id": asset(author).pk}], caption="Appelle 01 97 12 34 56"
    )
    assert post.visibility == Visibility.VISIBLE
    assert ModerationCase.objects.get(target_id=post.pk).labels == ["contact_outside"]


def test_a_muted_person_cannot_post():
    author = person()
    moderation.apply_sanction(author, actor=None, level="mute")
    with pytest.raises(Exception) as refused:
        services.create_post(author, kind="photo", media=[{"id": asset(author).pk}])
    assert refused.value.code == "restricted"


# --- The feed ------------------------------------------------------------------------------


def ids(rows):
    return [row.caption for row in rows]


def test_feed_followed_first_then_city_then_country():
    benin = CountryFactory()
    france = CountryFactory(
        code="FR", name="France", default_currency=CurrencyFactory(code="EUR", decimal_places=2)
    )
    me = person(city="Cotonou", country=benin)
    followed = person(name="Fifonsi", city="Abomey-Calavi", country=benin)
    neighbour = person(name="Gloria", city="Cotonou", country=benin)
    compatriot = person(name="Ruth", city="Porto-Novo", country=benin)
    far = person(name="Clarisse", city="Paris", country=france)
    Follow.objects.create(follower=me, followed=followed)

    published_post(far, caption="paris", likes=500, hours_ago=1)
    published_post(compatriot, caption="porto-novo", likes=100, hours_ago=1)
    published_post(neighbour, caption="cotonou", hours_ago=30)
    published_post(followed, caption="followed", hours_ago=60)
    published_post(me, caption="mine")

    rows, _ = feed(me)
    assert ids(rows) == ["followed", "cotonou", "porto-novo", "paris"]
    assert [row.tier for row in rows] == [0, 1, 2, 3]


def test_inside_a_tier_recency_and_interactions_count():
    me = person()
    a, b, c = person(name="A"), person(name="B"), person(name="C")
    published_post(a, caption="old-popular", hours_ago=48, likes=400)
    published_post(b, caption="fresh", hours_ago=1)
    published_post(c, caption="old-quiet", hours_ago=48)
    assert ids(feed(me)[0]) == ["old-popular", "fresh", "old-quiet"]

    PlatformSettingFactory(
        key="social.feed_weights", value_type="json", value='{"interactions": 0}'
    )
    assert ids(feed(me)[0])[0] == "fresh"


def test_distance_brings_closer_posts_up_when_her_position_is_known():
    me = person()
    near_author, far_author = person(name="Near"), person(name="Far")
    published_post(near_author, caption="near", location=Point(2.42, 6.37, srid=4326))
    published_post(far_author, caption="far", location=Point(2.62, 6.50, srid=4326))
    rows, _ = feed(me, near=Point(2.42, 6.37, srid=4326))
    assert ids(rows) == ["near", "far"]


def test_cursor_pages_without_duplicates_even_when_new_posts_arrive():
    PlatformSettingFactory(key="social.feed_page_size", value="2")
    me = person()
    for index in range(5):
        published_post(person(name=f"P{index}"), caption=f"post-{index}", hours_ago=index + 1)

    first, cursor = feed(me)
    published_post(person(name="Late"), caption="late", hours_ago=0)  # after the first page
    second, cursor2 = feed(me, cursor=cursor)
    third, cursor3 = feed(me, cursor=cursor2)
    seen = ids(first) + ids(second) + ids(third)
    assert seen == [f"post-{i}" for i in range(5)]
    assert cursor3 is None
    assert Cursor.decode("not-a-cursor") is None


def test_blocked_hidden_held_deleted_and_drafts_never_show():
    me = person()
    blocked_author = person(name="Blocked")
    hidden_author = person(name="Muted")
    published_post(blocked_author, caption="blocked")
    hidden = published_post(person(name="X"), caption="hidden")
    published_post(hidden_author, caption="author-hidden")
    published_post(person(name="Y"), caption="held", visibility=Visibility.HELD)
    published_post(person(name="Z"), caption="deleted", deleted_at=timezone.now())
    Post.objects.create(author=person(name="D"), kind="photo", caption="draft")
    published_post(person(name="OK"), caption="ok")

    moderation.block(me, blocked_author)
    moderation.hide(me, hidden)
    moderation.hide(me, hidden_author)
    assert ids(feed(me)[0]) == ["ok"]


def test_visitors_get_the_city_they_chose():
    published_post(person(name="A", city="Paris"), caption="paris")
    published_post(person(name="B", city="Cotonou"), caption="cotonou")
    rows, _ = feed(None, city="Cotonou")
    assert ids(rows) == ["cotonou", "paris"]
