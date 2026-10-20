from celery import shared_task

from .services import campaigns, giftcards, packages


@shared_task(bind=True, max_retries=3, default_retry_delay=120, ignore_result=True)
def deliver_campaign(self, campaign_id: str) -> int:
    return campaigns.deliver(campaign_id)


@shared_task(ignore_result=True)
def run_daily() -> dict:
    """Reminders of installments, packages and gift cards that expire."""
    return {
        "installments": packages.remind_installments(),
        "packages": packages.expire_packages(),
        "gift_cards": giftcards.expire(),
    }
