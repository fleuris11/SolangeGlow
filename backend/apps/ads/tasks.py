from celery import shared_task

from .services import boosts, campaigns


@shared_task(name="apps.ads.tasks.run")
def run() -> dict:
    """Every 5 minutes: campaigns and boosts past their time (or their impressions) end."""
    return {"campaigns": campaigns.end_due(), "boosts": boosts.end_due()}
