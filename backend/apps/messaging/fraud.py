"""Signs of a deal moving outside the app, looked for in messages written before any order.

Phone numbers, payment links and risky words (lists editable in the admin settings). The
message is still delivered: the conversation shows « Pay in the app to be protected ».
"""

from __future__ import annotations

import re
from collections.abc import Callable

from apps.core.selectors import get_setting
from apps.moderation.providers import PHONE, normalize

LINK = re.compile(r"(?:https?://)?(?:www\.)?([a-z0-9-]+(?:\.[a-z0-9-]+)+)(/\S*)?")

DEFAULT_KEYWORDS = [
    "western union",
    "moneygram",
    "mobile money",
    "momo",
    "orange money",
    "paypal",
    "virement",
    "iban",
    "lydia",
    "payer en dehors",
    "paie en dehors",
    "hors de l'appli",
]
DEFAULT_PAYMENT_DOMAINS = [
    "paypal.me",
    "paypal.com",
    "lydia-app.com",
    "pay.wave.com",
    "wise.com",
    "revolut.me",
    "buy.stripe.com",
    "me.fedapay.com",
]


def _list(key: str, default: list[str]) -> list[str]:
    return [normalize(word) for word in get_setting(key, default=default) or [] if word]


def check(text: str) -> list[str]:
    """Labels found: "phone", "payment_link", "keyword". Empty when nothing looks risky."""
    plain = normalize(text or "")
    if not plain:
        return []
    labels = []
    if PHONE.search(plain):
        labels.append("phone")
    domains = _list("messaging.payment_link_domains", DEFAULT_PAYMENT_DOMAINS)
    for match in LINK.finditer(plain):
        host = match.group(1)
        if any(host == domain or host.endswith("." + domain) for domain in domains):
            labels.append("payment_link")
            break
    for word in _list("messaging.fraud_keywords", DEFAULT_KEYWORDS):
        if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", plain):
            labels.append("keyword")
            break
    return labels


# --- Did they already deal through the app? ----------------------------------------------
# The shop and the bookings register a check: once an order or a booking exists between
# two people, numbers and links are normal (delivery, address), no warning any more.

TrustCheck = Callable[[object, object], bool]
_checks: list[TrustCheck] = []


def register_trust_check(check_fn: TrustCheck) -> None:
    if check_fn not in _checks:
        _checks.append(check_fn)


def unregister_trust_check(check_fn: TrustCheck) -> None:
    if check_fn in _checks:
        _checks.remove(check_fn)


def dealt_together(user, other) -> bool:
    return any(check_fn(user, other) for check_fn in _checks)
