"""Forbidden products: the words of the admin list, looked for in a product before it is
published (title, description, shades, sizes, colours).

Compared without accents or capitals; a long word is also found when written with spaces,
dashes or dots in between (« hydro-quinone », « H.Y.D.R.O.Q.U.I.N.O.N.E »).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from apps.core.selectors import get_setting

# Below this length a word is only matched whole (« fake » is not in « fakeeyelashes »).
GLUED_MIN_LENGTH = 6


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _glued(text: str) -> str:
    return re.sub(r"[^0-9a-z]", "", text)


@dataclass
class Finding:
    blocked: list[str] = field(default_factory=list)
    review: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    @property
    def terms(self) -> list[str]:
        return [*self.blocked, *self.review]


def _found(term: str, plain: str, tokens: set[str], glued: str) -> bool:
    if " " in term:
        if term in plain:
            return True
    elif term in tokens:
        return True
    compact = _glued(term)
    return len(compact) >= GLUED_MIN_LENGTH and compact in glued


def check_text(text: str) -> Finding:
    from .models import ForbiddenTerm

    plain = normalize(text)
    tokens = set(re.findall(r"\w+", plain))
    glued = _glued(plain)
    finding = Finding()
    for term in ForbiddenTerm.objects.filter(is_active=True).order_by("term"):
        if term.normalized and _found(term.normalized, plain, tokens, glued):
            target = (
                finding.blocked if term.action == ForbiddenTerm.Action.BLOCK else finding.review
            )
            target.append(term.term)
            if term.reason not in finding.reasons:
                finding.reasons.append(term.reason)
    # The older list of the moderation settings: sent to review as well.
    for word in get_setting("moderation.banned_product_words", default=[]) or []:
        word = normalize(str(word)).strip()
        if word and _found(word, plain, tokens, glued) and word not in finding.terms:
            finding.review.append(word)
    return finding


def product_text(product) -> str:
    variants = product.variants.all()
    parts = [product.title, product.description]
    parts += [f"{v.shade} {v.size} {v.color}" for v in variants]
    return "\n".join(parts)


def check_product(product) -> Finding:
    return check_text(product_text(product))
