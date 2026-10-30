"""Who helps before a ticket is sent. ``HelpAssistant`` is the interface: without
``HELP_AI_URL`` the search assistant suggests the answers of the FAQ that share the most
words with the question; with it, an AI service may answer simple questions (later)."""

from __future__ import annotations

import re
import unicodedata
from typing import Protocol

import httpx
from django.conf import settings
from django.db.models import Q

from apps.core.providers import ProviderError, ProviderNotConfigured

from .models import FaqItem

STOP = {
    "le", "la", "les", "un", "une", "des", "de", "du", "et", "ou", "a", "à", "je", "tu", "il",
    "elle", "on", "mon", "ma", "mes", "ton", "ta", "est", "pour", "comment", "que", "qui",
    "quoi", "the", "an", "is", "my", "how", "to", "what", "can", "i",
}  # fmt: skip


def words_of(text: str) -> set[str]:
    plain = unicodedata.normalize("NFKD", text.lower())
    plain = "".join(ch for ch in plain if not unicodedata.combining(ch))
    return {w for w in re.findall(r"[a-z0-9]{3,}", plain) if w not in STOP}


class HelpAssistant(Protocol):
    name: str

    def suggest(self, question: str, language: str, limit: int = 5) -> list[FaqItem]: ...

    def answer(self, question: str, language: str) -> str | None: ...


class SearchAssistant:
    name = "search"

    def suggest(self, question, language, limit=5):
        words = words_of(question)
        if not words:
            return []
        lang = language if language in ("fr", "en", "sk") else "fr"
        query = Q()
        for word in words:
            query |= Q(**{f"question_{lang}__icontains": word}) | Q(
                **{f"answer_{lang}__icontains": word}
            )
        found = list(FaqItem.objects.filter(is_published=True).filter(query)[:100])
        scored = sorted(
            found,
            key=lambda item: (
                -len(words & words_of(f"{item.question} {item.question} {item.answer}"))
            ),
        )
        return scored[:limit]

    def answer(self, question, language):
        return None


class AiHelpAssistant(SearchAssistant):
    """External service: POST {"question", "language", "faq"} → {"answer"}. Off without keys."""

    name = "ai"

    def answer(self, question, language):
        if not (settings.HELP_AI_URL and settings.HELP_AI_KEY):
            raise ProviderNotConfigured("help AI")
        faq = [
            {"q": item.question, "a": item.answer}
            for item in self.suggest(question, language, limit=8)
        ]
        try:
            response = httpx.post(
                settings.HELP_AI_URL,
                json={"question": question[:1000], "language": language, "faq": faq},
                headers={"Authorization": f"Bearer {settings.HELP_AI_KEY}"},
                timeout=settings.PROVIDERS_HTTP_TIMEOUT,
            )
            response.raise_for_status()
            return (response.json().get("answer") or "").strip() or None
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(str(exc)) from exc


def assistant() -> HelpAssistant:
    return AiHelpAssistant() if settings.HELP_AI_URL else SearchAssistant()
