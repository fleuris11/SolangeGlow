from celery import shared_task


@shared_task(acks_late=True)
def run_deadlines() -> dict:
    """Every 5 minutes: reminders, unanswered requests, waiting list, group shares."""
    from .services.automation import run_all

    return run_all()
