from celery import shared_task

from . import calls, services


@shared_task(acks_late=True)
def notify_unread(member_id: str) -> bool:
    """Grouped alert for the messages still unread a little after the first one."""
    return services.notify_unread(member_id)


@shared_task(name="apps.messaging.tasks.calls_minutely")
def calls_minutely() -> dict:
    """Calls ringing for nobody become missed; calls past the longest length are cut."""
    return calls.run_minutely()
