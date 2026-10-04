from celery import shared_task

from . import services


@shared_task(bind=True, max_retries=4, acks_late=True)
def deliver_notification(self, delivery_id: str) -> str:
    """Sends one channel; retries 1, 2, 4 then 8 minutes later before giving up."""
    try:
        return services.deliver(delivery_id)
    except services.RetryLater as exc:
        if self.request.retries >= self.max_retries:
            services.mark_failed(delivery_id)
            return "failed"
        raise self.retry(exc=exc, countdown=60 * 2**self.request.retries) from exc
