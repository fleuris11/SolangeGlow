"""Reads of the live rooms."""

from __future__ import annotations

from apps.core.models import Country

from . import registry, services


def country_of(user):
    if user is not None and user.is_authenticated and user.country_id:
        return user.country
    return Country.objects.filter(code="BJ").first()


def quota(user, now) -> dict:
    """Lives of her month and how many she may plan (no pro: nothing to plan)."""
    from apps.pros.models import ProProfile

    pro = ProProfile.objects.filter(user=user).select_related("country").first()
    if pro is None:
        return {"used": 0, "allowed": 0}
    start, stop = services.month_bounds(now)
    used = sum(source.count_in_month(pro, start, stop) for source in registry.all_sources())
    return {"used": used, "allowed": services.monthly_allowance(pro)}
