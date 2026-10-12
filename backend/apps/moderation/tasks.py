from celery import shared_task

from . import services


@shared_task
def lift_expired_sanctions() -> int:
    """Suspensions that have ended give the account back (every hour)."""
    return services.lift_expired_sanctions()
