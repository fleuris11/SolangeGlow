from celery import shared_task

from . import services


@shared_task(name="apps.live.tasks.run_minutely")
def run_minutely() -> dict:
    """Cuts the lives that went past the longest length; marks ready replays."""
    return services.run_minutely()


@shared_task(name="apps.live.tasks.run_daily")
def run_daily() -> int:
    """Deletes the replays past their time."""
    return services.expire_replays()
