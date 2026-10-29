"""The beauty quiz of the day: drafts prepared ahead of time, approved by the team in one
click, three questions with a picture and audio, points for each right answer."""

from __future__ import annotations

import datetime
import logging

from django.db import IntegrityError, transaction
from django.utils import timezone, translation

from apps.core.audit.services import record
from apps.core.providers import ProviderError, ProviderNotConfigured

from .. import errors
from ..generators import generator
from ..models import Action, QuizAnswer, QuizDay, QuizQuestion
from . import points
from .common import require_games, setting, today

logger = logging.getLogger("solangeglow.games")


def size() -> int:
    return max(1, int(setting("games.quiz_questions", 3)))


def of_day(day: datetime.date) -> QuizDay | None:
    return (
        QuizDay.objects.filter(date=day, status=QuizDay.Status.APPROVED)
        .prefetch_related("questions__image", "questions__audio")
        .first()
    )


def answers_of(user, quiz: QuizDay) -> dict:
    if user is None:
        return {}
    rows = QuizAnswer.objects.filter(user=user, question__quiz=quiz)
    return {row.question_id: row for row in rows}


@transaction.atomic
def answer(user, question_id, choice: int, *, now=None) -> dict:
    require_games(user)
    day = today(user, now)
    question = (
        QuizQuestion.objects.select_related("quiz")
        .filter(pk=question_id, quiz__date=day, quiz__status=QuizDay.Status.APPROVED)
        .first()
    )
    if question is None:
        raise errors.QuestionNotFound()
    if type(choice) is not int or not 1 <= choice <= len(question.choices()):
        raise errors.InvalidChoice()
    correct = choice == question.answer
    try:
        with transaction.atomic():
            QuizAnswer.objects.create(
                question=question, user=user, choice=choice, is_correct=correct
            )
    except IntegrityError as exc:
        raise errors.AlreadyAnswered() from exc
    entry = None
    if correct:
        entry = points.award(
            user,
            Action.QUIZ,
            key=f"quiz:{question.pk}:{user.pk}",
            source_type="quiz",
            source_id=question.pk,
            now=now,
        )
    return {
        "correct": correct,
        "answer": question.answer,
        "explanation": question.explanation,
        "gained": entry.amount if entry else 0,
    }


def check_complete(quiz: QuizDay) -> None:
    questions = list(quiz.questions.all())
    complete = [
        q for q in questions if q.text and len(q.choices()) >= 2 and q.answer <= len(q.choices())
    ]
    if len(complete) < size() or len(complete) != len(questions):
        raise errors.QuizIncomplete(details={"count": size()})


@transaction.atomic
def approve(quiz: QuizDay, *, actor) -> QuizDay:
    check_complete(quiz)
    quiz.status = QuizDay.Status.APPROVED
    quiz.approved_at = timezone.now()
    quiz.approved_by = actor
    quiz.save(update_fields=["status", "approved_at", "approved_by", "updated_at"])
    record("glow.quiz_approved", quiz, actor=actor)
    return quiz


def _draft(day: datetime.date) -> QuizDay:
    source = generator()
    try:
        proposals = source.questions(day, size(), "fr")
    except (ProviderError, ProviderNotConfigured) as exc:
        logger.warning("Quiz generator failed: %s", exc)
        proposals = []
    quiz = QuizDay.objects.create(date=day, generated_by=source.name)
    with translation.override("fr"):
        for position, item in enumerate(proposals):
            names = ("choice_1", "choice_2", "choice_3", "choice_4")
            values = dict(zip(names[: len(item.choices)], item.choices, strict=True))
            QuizQuestion.objects.create(
                quiz=quiz,
                position=position,
                text=item.text,
                answer=item.answer,
                explanation=item.explanation,
                **values,
            )
    return quiz


def prepare(*, now=None) -> int:
    """Drafts for the coming days (Celery Beat, every night): the team only approves."""
    start = timezone.localdate(now)
    ahead = int(setting("games.quiz_days_ahead", 7))
    created = 0
    for offset in range(1, ahead + 1):
        day = start + datetime.timedelta(days=offset)
        if not QuizDay.objects.filter(date=day).exists():
            _draft(day)
            created += 1
    return created
