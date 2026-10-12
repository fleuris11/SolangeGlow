from celery import shared_task

from . import services


@shared_task
def publish_due_posts() -> int:
    """Scheduled posts whose time has come go online (every minute)."""
    return services.publish_due_posts()
