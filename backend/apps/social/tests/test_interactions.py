import datetime

import pytest
from django.utils import timezone

from apps.moderation import services as moderation
from apps.notifications.models import Notification
from apps.pros.tests.factories import ProFactory
from apps.social import errors, selectors, services
from apps.social.models import Comment, Follow, Like, Story

from .factories import asset, person, published_post

pytestmark = pytest.mark.django_db


def test_like_is_counted_once_and_can_be_undone():
    post = published_post(person())
    fan = person(name="Inès")
    services.like(fan, post)
    services.like(fan, post)
    assert post.like_count == 1 and Like.objects.count() == 1
    services.unlike(fan, post)
    services.unlike(fan, post)
    assert post.like_count == 0


def test_save_and_list_saved_posts():
    post = published_post(person())
    fan = person(name="Inès")
    services.save(fan, post)
    assert post.save_count == 1
    assert list(selectors.saved_posts(fan)) == [post]
    services.unsave(fan, post)
    assert list(selectors.saved_posts(fan)) == []


def test_comments_with_one_level_of_replies_and_notifications():
    author = person(name="Aïcha")
    post = published_post(author)
    awa, ines = person(name="Awa"), person(name="Inès")
    first = services.comment(awa, post, "Trop beau !")
    reply = services.comment(ines, post, "Oui !", parent_id=first.pk)
    reply_to_reply = services.comment(author, post, "Merci", parent_id=reply.pk)
    assert reply.parent == first and reply_to_reply.parent == first  # never deeper
    post.refresh_from_db()
    assert post.comment_count == 3
    assert Notification.objects.filter(user=author, event_key="social.comment").count() == 2
    assert Notification.objects.filter(user=awa, event_key="social.reply").count() == 2

    listed = list(selectors.comments_of(post))
    assert listed == [first] and listed[0].visible_replies == [reply, reply_to_reply]

    services.delete_comment(reply, ines)
    post.refresh_from_db()
    assert post.comment_count == 2
    with pytest.raises(errors.NotYours):
        services.delete_comment(first, ines)
    services.delete_comment(first, author)  # the author of the post can clean up


def test_blocked_people_cannot_comment_or_follow_each_other():
    author, troll = person(), person(name="Troll")
    post = published_post(author)
    services.follow(troll, author)
    moderation.block(author, troll)
    assert not Follow.objects.exists()  # blocking ends the follow
    with pytest.raises(errors.Blocked):
        services.comment(troll, post, "Hello")
    with pytest.raises(errors.Blocked):
        services.follow(troll, author)


def test_follow_notifies_and_cannot_follow_yourself():
    pro, fan = ProFactory().user, person(name="Awa")
    services.follow(fan, pro)
    services.follow(fan, pro)
    assert Follow.objects.filter(follower=fan).count() == 1
    assert Notification.objects.filter(user=pro, event_key="social.new_follower").count() == 1
    assert list(selectors.following_of(fan)) == [pro]
    services.unfollow(fan, pro)
    assert not Follow.objects.exists()
    with pytest.raises(errors.CannotFollowYourself):
        services.follow(fan, fan)


def test_share_is_counted():
    post = published_post(person())
    services.record_share(None, post, "whatsapp")
    services.record_share(person(name="B"), post, "unknown-network")
    post.refresh_from_db()
    assert post.share_count == 2


# --- Stories -------------------------------------------------------------------------------


def test_story_kinds_and_their_rules():
    author = person()
    photo = services.create_story(author, kind="photo", media_id=asset(author, purpose="story").pk)
    assert photo.expires_at > timezone.now() + datetime.timedelta(hours=23)
    text = services.create_story(author, kind="text", text="Promo -20 % ce samedi", background="or")
    assert text.background == "or"
    with pytest.raises(errors.InvalidStory):
        services.create_story(author, kind="text", text="  ")
    with pytest.raises(errors.InvalidStory):
        services.create_story(author, kind="photo", media_id=asset(author).pk)  # a post picture
    with pytest.raises(errors.NotAPro):
        services.create_story(author, kind="free_slots", slots=["14:00"])


def test_free_slots_story_of_a_pro():
    pro = ProFactory()
    story = services.create_story(pro.user, kind="free_slots", slots=["16:30", "14:00", "14:00"])
    assert story.slots == ["14:00", "16:30"] and story.pro == pro
    with pytest.raises(errors.InvalidSlots):
        services.create_story(pro.user, kind="free_slots", slots=["25:00"])


def test_story_tray_followed_first_unseen_first_and_expired_gone():
    me = person(city="Cotonou")
    followed, neighbour, far = person(name="F"), person(name="N"), person(name="X", city="Paris")
    services.follow(me, followed)
    services.create_story(far, kind="text", text="Paris")
    services.create_story(neighbour, kind="text", text="Cotonou")
    seen = services.create_story(followed, kind="text", text="Suivie")
    old = services.create_story(neighbour, kind="text", text="Vieille")
    Story.objects.filter(pk=old.pk).update(expires_at=timezone.now())

    tray = selectors.story_tray(me)
    assert [entry["author"] for entry in tray] == [followed, neighbour, far]
    assert [len(entry["stories"]) for entry in tray] == [1, 1, 1]

    services.mark_seen(seen, me)
    assert selectors.story_tray(me)[0]["seen"] is True
    assert selectors.has_live_story([followed.pk, me.pk]) == {followed.pk}


def test_comment_moderation_hides_and_recounts():
    from apps.core.tests.factories import PlatformSettingFactory

    PlatformSettingFactory(key="moderation.blocked_words", value_type="json", value='["pute"]')
    post = published_post(person())
    services.comment(person(name="Troll"), post, "espèce de pute")
    post.refresh_from_db()
    assert post.comment_count == 0
    assert Comment.objects.get().visibility == "held"
