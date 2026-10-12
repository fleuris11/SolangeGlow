"""Automatic checks of texts and pictures (ADR-003: providers behind an interface).

- RulesModerationProvider: word lists edited in the admin (platform settings) and a few
  patterns (contact or payment outside the app, shouting). Always active.
- AiModerationProvider: an external moderation service, ready but used only when
  MODERATION_AI_URL and MODERATION_AI_KEY are set; otherwise ProviderNotConfigured.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Protocol

import httpx
from django.conf import settings

from apps.core.providers import ProviderError, ProviderNotConfigured
from apps.core.selectors import get_setting

ALLOW, REVIEW, BLOCK = "allow", "review", "block"
SEVERITY = {ALLOW: 0, REVIEW: 1, BLOCK: 2}


@dataclass
class Verdict:
    action: str = ALLOW
    labels: list[str] = field(default_factory=list)
    provider: str = ""

    def worst(self, other: Verdict) -> Verdict:
        if SEVERITY[other.action] > SEVERITY[self.action]:
            return Verdict(other.action, sorted({*self.labels, *other.labels}), other.provider)
        return Verdict(self.action, sorted({*self.labels, *other.labels}), self.provider)


class ModerationProvider(Protocol):
    name: str

    def check_text(self, text: str, *, language: str = "fr") -> Verdict: ...

    def check_image(self, url: str) -> Verdict: ...


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _words(key: str) -> list[str]:
    return [normalize(w) for w in get_setting(key, default=[]) if str(w).strip()]


PHONE = re.compile(r"(?:\+?\d[\s.-]?){8,}")
OUTSIDE_PAYMENT = re.compile(
    r"\b(western union|moneygram|paie(?:z|r)? (?:hors|en dehors)|pay outside|virement direct)\b"
)


class RulesModerationProvider:
    """Word lists and patterns. Cannot look at pictures: they are allowed."""

    name = "rules"

    def check_text(self, text: str, *, language: str = "fr") -> Verdict:
        plain = normalize(text or "")
        if not plain.strip():
            return Verdict(provider=self.name)
        tokens = set(re.findall(r"\w+", plain))

        def found(words: list[str]) -> bool:
            return any((w in tokens) if " " not in w else (w in plain) for w in words)

        verdict = Verdict(provider=self.name)
        if found(_words("moderation.blocked_words")):
            return Verdict(BLOCK, ["blocked_word"], self.name)
        labels = []
        if found(_words("moderation.review_words")):
            labels.append("sensitive_word")
        if OUTSIDE_PAYMENT.search(plain):
            labels.append("payment_outside")
        if get_setting("moderation.flag_phone_numbers", default=True) and PHONE.search(plain):
            labels.append("contact_outside")
        letters = [c for c in text if c.isalpha()]
        if len(letters) >= 20 and sum(c.isupper() for c in letters) / len(letters) > 0.8:
            labels.append("shouting")
        if labels:
            verdict = Verdict(REVIEW, labels, self.name)
        return verdict

    def check_image(self, url: str) -> Verdict:
        return Verdict(provider=self.name)


class AiModerationProvider:
    """External moderation API (a JSON answer {"flagged": bool, "categories": {...}})."""

    name = "ai"

    def _configured(self):
        if not (settings.MODERATION_AI_URL and settings.MODERATION_AI_KEY):
            raise ProviderNotConfigured("moderation AI")

    def _ask(self, payload: dict) -> Verdict:
        self._configured()
        try:
            response = httpx.post(
                settings.MODERATION_AI_URL,
                json=payload,
                headers={"Authorization": f"Bearer {settings.MODERATION_AI_KEY}"},
                timeout=settings.PROVIDERS_HTTP_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(str(exc)) from exc
        labels = sorted(k for k, v in (data.get("categories") or {}).items() if v)
        if not data.get("flagged"):
            return Verdict(provider=self.name)
        severe = set(get_setting("moderation.ai_block_categories", default=["sexual/minors"]))
        action = BLOCK if severe & set(labels) else REVIEW
        return Verdict(action, labels or ["flagged"], self.name)

    def check_text(self, text: str, *, language: str = "fr") -> Verdict:
        return self._ask({"input": text, "language": language})

    def check_image(self, url: str) -> Verdict:
        return self._ask({"image_url": url})


def providers() -> list[ModerationProvider]:
    return [RulesModerationProvider(), AiModerationProvider()]


def check(*, text: str = "", image_urls: list[str] | None = None, language: str = "fr") -> Verdict:
    """The worst verdict of every provider that is configured."""
    verdict = Verdict()
    for provider in providers():
        try:
            if text:
                verdict = verdict.worst(provider.check_text(text, language=language))
            for url in image_urls or []:
                verdict = verdict.worst(provider.check_image(url))
        except ProviderNotConfigured:
            continue
        except ProviderError:
            # The service is down: keep the content visible but put it in the queue.
            verdict = verdict.worst(Verdict(REVIEW, ["check_failed"], provider.name))
    return verdict
