"""Who prepares the quizzes and the challenge themes ahead of time.

``QuizGenerator`` is the interface. Without ``QUIZ_AI_URL`` the manual generator gives
empty drafts that the team fills in the admin; with it, an external AI service proposes
questions and themes. Either way nothing is shown before an approval in one click.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Protocol

import httpx
from django.conf import settings

from apps.core.providers import ProviderError, ProviderNotConfigured


@dataclass(frozen=True)
class DraftQuestion:
    text: str
    choices: list[str] = field(default_factory=list)
    answer: int = 1  # 1 to 4
    explanation: str = ""


@dataclass(frozen=True)
class DraftTheme:
    theme: str
    description: str = ""


class QuizGenerator(Protocol):
    name: str

    def questions(self, day: datetime.date, count: int, language: str) -> list[DraftQuestion]: ...

    def theme(self, starts_on: datetime.date, language: str) -> DraftTheme | None: ...


class ManualGenerator:
    """No AI: an empty draft, written by the team in the admin."""

    name = "manual"

    def questions(self, day, count, language):
        return []

    def theme(self, starts_on, language):
        return None


class AiGenerator:
    """External service: POST {"kind", "day", "count", "language"} → JSON proposals."""

    name = "ai"

    def _ask(self, payload: dict) -> dict:
        if not (settings.QUIZ_AI_URL and settings.QUIZ_AI_KEY):
            raise ProviderNotConfigured("quiz AI")
        try:
            response = httpx.post(
                settings.QUIZ_AI_URL,
                json=payload,
                headers={"Authorization": f"Bearer {settings.QUIZ_AI_KEY}"},
                timeout=settings.PROVIDERS_HTTP_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(str(exc)) from exc

    def questions(self, day, count, language):
        data = self._ask(
            {"kind": "quiz", "day": day.isoformat(), "count": count, "language": language}
        )
        found = []
        for item in (data.get("questions") or [])[:count]:
            choices = [str(c)[:80] for c in (item.get("choices") or [])][:4]
            answer = int(item.get("answer") or 0)
            if item.get("text") and len(choices) >= 2 and 1 <= answer <= len(choices):
                found.append(
                    DraftQuestion(
                        text=str(item["text"])[:200],
                        choices=choices,
                        answer=answer,
                        explanation=str(item.get("explanation") or "")[:300],
                    )
                )
        return found

    def theme(self, starts_on, language):
        data = self._ask({"kind": "challenge", "day": starts_on.isoformat(), "language": language})
        if not data.get("theme"):
            return None
        return DraftTheme(str(data["theme"])[:80], str(data.get("description") or "")[:240])


def generator() -> QuizGenerator:
    return AiGenerator() if settings.QUIZ_AI_URL else ManualGenerator()
