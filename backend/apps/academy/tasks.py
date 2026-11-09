"""Scheduled work of the academy (Celery Beat)."""

from celery import shared_task

from .services import enrollments, lives, passes


@shared_task(ignore_result=True)
def run_frequent() -> dict:
    """Every 5 minutes: reminders of the lives, lives that are over."""
    return {"reminders": lives.send_reminders(), "closed": lives.close_lives()}


@shared_task(ignore_result=True)
def run_daily() -> dict:
    """Every day: the pass (reminders, months not paid), courses bought but never opened."""
    return {
        "renewals": passes.send_renewals(),
        "ended": passes.end_periods(),
        "released": enrollments.release_unstarted(),
    }


@shared_task(acks_late=True)
def notify_live_followers(live_id: str) -> int:
    """A training live is on air: the people who follow its professional are told too (those
    registered already were, by the live itself)."""
    from apps.notifications.services import notify
    from apps.social.models import Follow

    from .live_source import room_link
    from .models import LiveRegistration, LiveSession

    live = LiveSession.objects.select_related("pro__user").filter(pk=live_id).first()
    if live is None or live.pro is None:
        return 0
    registered = set(LiveRegistration.objects.filter(live=live).values_list("user_id", flat=True))
    count = 0
    followers = Follow.objects.filter(followed=live.pro.user).select_related("follower")
    for follow in followers.iterator():
        if follow.follower_id in registered:
            continue
        notify(
            follow.follower, "academy.live_on_air", {"live": live.title}, link=room_link(live.pk)
        )
        count += 1
    return count
