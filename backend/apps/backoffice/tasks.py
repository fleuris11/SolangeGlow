from celery import shared_task

from .services import prospects


@shared_task(name="apps.backoffice.tasks.run_daily")
def run_daily() -> dict:
    """Every night: prospects whose showcase is now published become active."""
    return {"prospects_active": prospects.promote_active()}
