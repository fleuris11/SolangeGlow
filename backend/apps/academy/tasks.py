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
