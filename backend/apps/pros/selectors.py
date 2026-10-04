from .models import Trade


def active_trades():
    return Trade.objects.filter(is_active=True).order_by("position", "key")
