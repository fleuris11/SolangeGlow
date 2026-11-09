"""A modern live: the host replies, takes a comment away, turns the comments off, blocks
someone; she sees who is watching; followers are told; she gets her figures at the end."""

import pytest
from django.utils import timezone

from apps.live import errors, services
from apps.live.models import LiveAttendance, LiveQuestion, LiveRoom
from apps.messaging.tests.factories import adult
from apps.notifications.models import Notification
from apps.social.models import Follow

from .test_rooms import T, events, on_air, planned, registered

pytestmark = pytest.mark.django_db


def test_the_host_replies_and_takes_a_comment_away(fake_livekit):
    live, student = on_air(fake_livekit)
    host = live.pro.user
    comment = services.ask(student, T, live.pk, "Ça tient combien de temps ?")

    with pytest.raises(errors.NotHost):
        services.reply(student, T, live.pk, comment.pk, "Moi aussi")
    with pytest.raises(errors.EmptyReply):
        services.reply(host, T, live.pk, comment.pk, " ")
    services.reply(host, T, live.pk, comment.pk, "Toute la soirée.")
    shown = services.state(student, T, live.pk)["questions"][0]
    assert shown["reply"] == "Toute la soirée." and shown["answered"]
    # Only the host learns who wrote it (to block her).
    assert shown["author_id"] is None
    assert services.state(host, T, live.pk)["questions"][0]["author_id"] == student.pk

    services.remove_comment(host, T, live.pk, comment.pk)
    assert services.state(student, T, live.pk)["questions"] == []


def test_comments_off_then_a_block(fake_livekit):
    live, student = on_air(fake_livekit)
    host = live.pro.user
    services.set_comments(host, T, live.pk, off=True)
    state = services.state(student, T, live.pk)
    assert state["comments_off"] and not state["can_ask"]
    with pytest.raises(errors.CommentsOff):
        services.ask(student, T, live.pk, "Bonjour")
    # The host still writes, even with the comments off.
    services.ask(host, T, live.pk, "Je reviens à vos questions dans 5 minutes.")

    services.set_comments(host, T, live.pk, off=False)
    comment = services.ask(student, T, live.pk, "Pub pour mon site !")
    services.block(host, T, live.pk, student.pk)
    comment.refresh_from_db()
    assert comment.visibility == LiveQuestion.Visibility.REMOVED
    assert not services.state(student, T, live.pk)["can_ask"]
    with pytest.raises(errors.BlockedInLive):
        services.ask(student, T, live.pk, "Encore moi")
    with pytest.raises(errors.NotHost):
        services.block(student, T, live.pk, host.pk)


def test_the_host_sees_who_is_watching(fake_livekit):
    live, student = on_air(fake_livekit)
    room = LiveRoom.objects.get(source_id=live.pk)
    LiveAttendance.objects.create(room=room, identity=str(student.pk), joined_at=timezone.now())
    LiveAttendance.objects.create(room=room, identity="guest-abc", joined_at=timezone.now())
    people = services.state(live.pro.user, T, live.pk)["people"]
    assert [person["name"] for person in people] == [student.first_name]
    assert services.state(student, T, live.pk)["people"] == []


def test_followers_are_told_and_the_host_gets_her_figures(fake_livekit):
    live = planned()
    fan = adult("Mariam")
    Follow.objects.create(follower=fan, followed=live.pro.user)
    student = registered(live)
    Follow.objects.create(follower=student, followed=live.pro.user)
    services.start(live.pro.user, T, live.pk)
    assert "academy.live_on_air" in events(fan)
    # Registered and following: told once.
    told = Notification.objects.filter(user=student, event_key="academy.live_on_air")
    assert told.count() == 1

    services.end_by_host(live.pro.user, T, live.pk)
    assert "live.summary" in events(live.pro.user)
