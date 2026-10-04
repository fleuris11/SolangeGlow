"""Read-only rules about accounts, used by other modules (shop, messaging, profiles)."""

from __future__ import annotations

import datetime

from django.utils import timezone

from apps.core.selectors import get_setting


def age_on(birth_date: datetime.date, today: datetime.date | None = None) -> int:
    today = today or timezone.localdate()
    years = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        years -= 1
    return years


def _country(user) -> str | None:
    return user.country.code if user.country_id else None


def is_minor(user) -> bool:
    """Under the adult age of the platform. Unknown birth date counts as minor (safe side)."""
    if user.birth_date is None:
        return True
    adult = int(get_setting("accounts.adult_age", country=_country(user), default=18))
    return age_on(user.birth_date) < adult


def can_purchase(user) -> bool:
    if not is_minor(user):
        return True
    return bool(get_setting("accounts.minors_can_purchase", country=_country(user), default=False))


def can_receive_message_from(user, sender, *, sender_is_followed: bool = False) -> bool:
    """Young accounts do not get private messages from strangers (spec: protection of minors)."""
    if not is_minor(user) or sender_is_followed:
        return True
    return bool(
        get_setting(
            "accounts.minors_receive_messages_from_strangers",
            country=_country(user),
            default=False,
        )
    )


def is_visible(user) -> bool:
    """Shown to other people: active, not deleted, no deletion pending."""
    return user.is_active and user.deleted_at is None and user.deletion_requested_at is None
