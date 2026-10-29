"""Levels of the pros (New, Confirmed, Top pro), computed every night from what she did
(appointments done, orders handed over) and her verified reviews. Advantage: ahead of
the pros equal to her in the search, and a badge on her showcase."""

from __future__ import annotations

from django.db.models import Avg, Count, Q
from django.utils import timezone

from apps.booking.models import Appointment
from apps.notifications.services import notify
from apps.pros.models import Level, ProProfile
from apps.shop.models import Order
from apps.social.models import Review, Visibility

from .common import setting

DEFAULT_RULES = {
    "confirmed": {"done": 10, "reviews": 5, "average": 4.0, "verified": False},
    "top": {"done": 50, "reviews": 20, "average": 4.6, "verified": True},
}


def rules() -> dict:
    found = setting("games.pro_levels", {}) or {}
    return {name: {**DEFAULT_RULES[name], **(found.get(name) or {})} for name in DEFAULT_RULES}


def stats(pro: ProProfile) -> dict:
    done = Appointment.objects.filter(pro=pro, status=Appointment.Status.COMPLETED).count()
    done += Order.objects.filter(pro=pro, status=Order.Status.COMPLETED).count()
    reviews = Review.objects.filter(pro=pro, visibility=Visibility.VISIBLE).aggregate(
        n=Count("id"), average=Avg("rating")
    )
    return {
        "done": done,
        "reviews": reviews["n"] or 0,
        "average": float(reviews["average"] or 0),
        "verified": pro.is_verified,
    }


def _meets(found: dict, rule: dict) -> bool:
    return (
        found["done"] >= int(rule["done"])
        and found["reviews"] >= int(rule["reviews"])
        and found["average"] >= float(rule["average"])
        and (found["verified"] or not rule.get("verified"))
    )


def level_of(pro: ProProfile) -> int:
    found, levels = stats(pro), rules()
    if _meets(found, levels["top"]):
        return Level.TOP
    if _meets(found, levels["confirmed"]):
        return Level.CONFIRMED
    return Level.NEW


def refresh(pro: ProProfile) -> int:
    level = level_of(pro)
    if level != pro.level:
        risen = level > pro.level
        ProProfile.objects.filter(pk=pro.pk).update(level=level, level_at=timezone.now())
        if risen:
            notify(pro.user, "glow.pro_level_up", {"level": Level(level).label}, link="/pro")
    return level


def refresh_all() -> int:
    """Celery Beat, every night. Returns how many pros changed level."""
    changed = 0
    pros = ProProfile.objects.filter(
        Q(status=ProProfile.Status.PUBLISHED) | ~Q(level=Level.NEW)
    ).select_related("user")
    for pro in pros.iterator():
        before = pro.level
        changed += refresh(pro) != before
    return changed
