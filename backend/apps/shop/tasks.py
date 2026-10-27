from celery import shared_task


@shared_task(acks_late=True)
def run_alerts() -> int:
    """Every 15 minutes: flash sales that just started (price drops for wishlists)."""
    from .services.alerts import announce_flash_sales

    return announce_flash_sales()


@shared_task(acks_late=True)
def notify_live_followers(sale_live_id: str) -> int:
    """A sales live is on air: the people who follow the shop are told (once each)."""
    from apps.notifications.services import notify
    from apps.social.models import Follow

    from .live_source import room_link
    from .models import SaleLive

    live = SaleLive.objects.select_related("pro__user").filter(pk=sale_live_id).first()
    if live is None:
        return 0
    count = 0
    followers = Follow.objects.filter(followed=live.pro.user).select_related("follower")
    for follow in followers.iterator():
        notify(
            follow.follower,
            "shop.live_on_air",
            {"shop": live.pro.display_name, "live": live.title},
            link=room_link(live.pk),
        )
        count += 1
    return count
