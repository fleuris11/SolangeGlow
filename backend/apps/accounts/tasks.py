from smtplib import SMTPException

from celery import shared_task

from . import services


@shared_task(bind=True, max_retries=3, acks_late=True)
def send_otp_code(self, challenge_id: str) -> str:
    """Tries each channel in order; if all fail, tries again 15 s, 30 s, then 60 s later."""
    try:
        return services.send_challenge(challenge_id)
    except services.CodeNotSentYet as exc:
        if self.request.retries >= self.max_retries:
            services.mark_delivery_failed(challenge_id)
            return "failed"
        raise self.retry(exc=exc, countdown=15 * 2**self.request.retries) from exc


@shared_task(bind=True, max_retries=4, acks_late=True)
def send_account_link(self, user_id: str, kind: str) -> str:
    """Confirmation, new password or « you already have an account »: tried again 30 s, 1, 2
    and 4 minutes later when the e-mail service refuses."""
    try:
        return services.deliver_link(user_id, kind)
    except (SMTPException, OSError) as exc:
        if self.request.retries >= self.max_retries:
            services.logger.warning(
                "Account e-mail not delivered (%s): %s", kind, type(exc).__name__
            )
            return "failed"
        raise self.retry(exc=exc, countdown=30 * 2**self.request.retries) from exc


@shared_task
def purge_deleted_accounts() -> int:
    """Daily: accounts whose deletion grace period is over are anonymised."""
    return services.purge_due_deletions()
