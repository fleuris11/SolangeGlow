from celery import shared_task

from . import services


@shared_task(ignore_result=True)
def run_subscriptions() -> dict:
    """Renewals, ends of trial, unpaid months, back to the free plan (every hour)."""
    return services.run_all()
