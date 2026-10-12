from celery import shared_task

from . import services


@shared_task(acks_late=True)
def notify_unread(member_id: str) -> bool:
    """Grouped alert for the messages still unread a little after the first one."""
    return services.notify_unread(member_id)
