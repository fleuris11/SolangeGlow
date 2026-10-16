from celery import shared_task


@shared_task(acks_late=True)
def run_deadlines() -> dict:
    """Every 15 minutes: group pre-orders that end, quotes that expire."""
    from .services import run_all

    return run_all()
