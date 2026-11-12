from smtplib import SMTPException

from celery import shared_task

from .services import prospects


@shared_task(name="apps.backoffice.tasks.run_daily")
def run_daily() -> dict:
    """Every night: prospects whose showcase is now published become active."""
    return {"prospects_active": prospects.promote_active()}


@shared_task(bind=True, max_retries=4, acks_late=True)
def send_prospect_message(self, message_id: str) -> str:
    """One e-mail to a prospect: tried again 1, 2, 4 and 8 minutes later when refused."""
    try:
        return prospects.deliver(message_id)
    except (SMTPException, OSError) as exc:
        if self.request.retries >= self.max_retries:
            prospects.mark_failed(message_id, type(exc).__name__)
            return "failed"
        raise self.retry(exc=exc, countdown=60 * 2**self.request.retries) from exc
