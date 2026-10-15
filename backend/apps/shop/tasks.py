from celery import shared_task


@shared_task(acks_late=True)
def run_alerts() -> int:
    """Every 15 minutes: flash sales that just started (price drops for wishlists)."""
    from .services.alerts import announce_flash_sales

    return announce_flash_sales()
