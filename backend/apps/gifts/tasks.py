from celery import shared_task

from . import services


@shared_task(name="apps.gifts.tasks.run")
def run() -> dict:
    """Gifts of the day sent, one reminder for the forgotten ones, past ones closed."""
    return {
        "sent": services.send_due(),
        "reminded": services.remind(),
        "expired": services.expire(),
    }
