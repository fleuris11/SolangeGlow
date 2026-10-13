"""Commission and buyer protection fee: the most precise active rule wins.

Precision: seller (8) > category (4) > country (2) > purpose (1); then the priority, then
the newest rule. A rule with a currency only applies to that currency.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Q
from django.utils import timezone

from .models import PricingRule


@dataclass(frozen=True)
class Charge:
    rule: PricingRule | None
    amount_minor: int


def _score(rule: PricingRule) -> tuple:
    precision = (
        8 * bool(rule.seller_id)
        + 4 * bool(rule.category)
        + 2 * bool(rule.country)
        + bool(rule.purpose)
    )
    return (precision, rule.priority, rule.created_at)


def find_rule(
    kind: str,
    *,
    currency: str,
    country: str = "",
    category: str = "",
    seller=None,
    purpose: str = "",
    at=None,
) -> PricingRule | None:
    at = at or timezone.now()
    rules = PricingRule.objects.filter(kind=kind, is_active=True).filter(
        Q(currency="") | Q(currency=currency),
        Q(country="") | Q(country=country),
        Q(category="") | Q(category=category),
        Q(seller__isnull=True) | Q(seller=seller),
        Q(purpose="") | Q(purpose=purpose),
        Q(valid_from__isnull=True) | Q(valid_from__lte=at),
        Q(valid_until__isnull=True) | Q(valid_until__gt=at),
    )
    return max(rules, key=_score, default=None)


def amount_for(rule: PricingRule | None, base_minor: int) -> int:
    """Rate (rounded half up to the smallest unit) plus fixed amount, within min and max."""
    if rule is None or base_minor <= 0:
        return 0
    value = (base_minor * rule.percent_bps + 5_000) // 10_000 + rule.fixed_minor
    if rule.min_minor is not None:
        value = max(value, rule.min_minor)
    if rule.max_minor is not None:
        value = min(value, rule.max_minor)
    return max(value, 0)


def charge(kind: str, base_minor: int, **criteria) -> Charge:
    rule = find_rule(kind, **criteria)
    return Charge(rule, amount_for(rule, base_minor))
