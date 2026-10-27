"""Watching: where she stopped, lessons watched, quizzes, the end of the course with its
certificate and, for a pro, the « Trained on Solange Glow » badge."""

from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.audit.services import record
from apps.core.media.services import variant_url
from apps.notifications.services import notify

from .. import errors, selectors
from ..models import Certificate, Enrollment, Lesson, LessonProgress, Module, QuizAttempt
from .common import LINK, certificate_code, lessons_of, setting
from .enrollments import started

E = Enrollment.Status


def find_lesson(lesson_id, viewer) -> Lesson:
    lesson = (
        Lesson.objects.select_related(
            "module__course__pro__user", "module__course__country", "video"
        )
        .filter(pk=lesson_id)
        .first()
    )
    if lesson is None:
        raise errors.CourseNotFound()
    course = lesson.module.course
    if course.status == course.Status.PUBLISHED or selectors.is_trainer(viewer, course):
        return lesson
    enrollment = selectors.enrollment_of(viewer, course)
    if enrollment is not None and enrollment.status == E.ACTIVE:
        return lesson  # bought before the course left the catalogue: she keeps it
    raise errors.CourseNotFound()


def _video_ttl(course) -> int:
    return int(setting("academy.video_url_ttl_seconds", course.country, 3600))


def playback(user, lesson: Lesson) -> dict:
    """Links of the two qualities (signed, long enough for a whole lesson), resources, where
    she stopped. Opening a lesson counts as starting the course."""
    course = lesson.module.course
    enrollment = selectors.enrollment_of(user, course)
    allowed = lesson.is_preview or selectors.can_watch(user, course, enrollment)
    if not allowed:
        if course.pricing == course.Pricing.PASS and not selectors.has_pass(user):
            raise errors.PassRequired()
        raise errors.NotEnrolled()
    position = 0
    if enrollment is not None and enrollment.status == E.ACTIVE:
        with transaction.atomic():
            started(enrollment)
            progress = _progress(enrollment, lesson)
            position = progress.position_seconds
            if enrollment.last_lesson_id != lesson.pk:
                enrollment.last_lesson = lesson
                enrollment.save(update_fields=["last_lesson", "updated_at"])
    video = lesson.video
    ttl = _video_ttl(course)
    urls = {}
    if video is not None and video.is_ready:
        urls = {name: variant_url(video, name, ttl=ttl) for name in ("low", "medium")}
        urls["poster"] = variant_url(video, "poster_medium") or variant_url(video, "poster_large")
    resources = [
        {
            "id": str(resource.pk),
            "title": resource.title,
            "url": variant_url(resource.file, "file", ttl=ttl)
            if resource.file is not None and resource.file.is_ready
            else None,
        }
        for resource in lesson.resources.select_related("file")
    ]
    return {
        "lesson": lesson,
        "urls": urls,
        "resources": resources,
        "position_seconds": position,
        "expires_in": ttl,
    }


def _progress(enrollment: Enrollment, lesson: Lesson) -> LessonProgress:
    try:
        with transaction.atomic():
            progress, _ = LessonProgress.objects.get_or_create(enrollment=enrollment, lesson=lesson)
    except IntegrityError:  # two tabs at once
        progress = LessonProgress.objects.get(enrollment=enrollment, lesson=lesson)
    return progress


def _active_enrollment(user, course) -> Enrollment:
    enrollment = selectors.enrollment_of(user, course)
    if enrollment is None or not selectors.can_watch(user, course, enrollment):
        raise errors.NotEnrolled()
    return enrollment


@transaction.atomic
def save_position(user, lesson: Lesson, *, seconds: int, ended: bool = False) -> Enrollment:
    """Every few seconds while she watches, and at the end: resume, lessons watched."""
    course = lesson.module.course
    enrollment = _active_enrollment(user, course)
    progress = _progress(enrollment, lesson)
    length = lesson.duration_seconds or 0
    seconds = max(0, min(int(seconds), length or int(seconds)))
    progress.position_seconds = seconds
    share = int(setting("academy.watched_percent", course.country, 90))
    if progress.completed_at is None and (ended or (length and seconds * 100 >= length * share)):
        progress.completed_at = timezone.now()
    progress.save()
    return refresh(enrollment)


def refresh(enrollment: Enrollment) -> Enrollment:
    """Progress bar: lessons watched and quizzes passed; the end of the course."""
    course = enrollment.course
    lesson_ids = list(lessons_of(course).values_list("pk", flat=True))
    done = LessonProgress.objects.filter(
        enrollment=enrollment, lesson_id__in=lesson_ids, completed_at__isnull=False
    ).count()
    quiz_modules = set(
        Module.objects.filter(course=course, questions__isnull=False).values_list("pk", flat=True)
    )
    passed = set(
        QuizAttempt.objects.filter(
            enrollment=enrollment, module_id__in=quiz_modules, passed=True
        ).values_list("module_id", flat=True)
    )
    steps = len(lesson_ids) + len(quiz_modules)
    percent = round((done + len(passed)) * 100 / steps) if steps else 0
    enrollment.progress_percent = min(100, percent)
    fields = ["progress_percent", "updated_at"]
    finished = steps and done == len(lesson_ids) and passed == quiz_modules
    if finished and enrollment.completed_at is None:
        enrollment.completed_at = timezone.now()
        fields.append("completed_at")
        enrollment.save(update_fields=fields)
        _finished(enrollment)
        return enrollment
    enrollment.save(update_fields=fields)
    return enrollment


def quiz_of(user, module: Module) -> dict:
    enrollment = _active_enrollment(user, module.course)
    questions = list(module.questions.all())
    last = QuizAttempt.objects.filter(enrollment=enrollment, module=module).first()
    return {
        "module": module,
        "questions": questions,
        "unlocked": _all_watched(enrollment, module),
        "passed": QuizAttempt.objects.filter(
            enrollment=enrollment, module=module, passed=True
        ).exists(),
        "last_score": last.score_percent if last else None,
        "pass_percent": _pass_percent(module),
    }


def _pass_percent(module: Module) -> int:
    return int(setting("academy.quiz_pass_percent", module.course.country, 70))


def _all_watched(enrollment: Enrollment, module: Module) -> bool:
    lesson_ids = set(module.lessons.values_list("pk", flat=True))
    done = set(
        LessonProgress.objects.filter(
            enrollment=enrollment, lesson_id__in=lesson_ids, completed_at__isnull=False
        ).values_list("lesson_id", flat=True)
    )
    return lesson_ids <= done


@transaction.atomic
def submit_quiz(user, module: Module, answers: list) -> dict:
    enrollment = _active_enrollment(user, module.course)
    if not _all_watched(enrollment, module):
        raise errors.QuizLocked()
    questions = list(module.questions.all())
    if not questions or len(answers) != len(questions):
        raise errors.InvalidAnswers()
    if any(type(a) is not int for a in answers):
        raise errors.InvalidAnswers()
    right = [q.correct == a for q, a in zip(questions, answers, strict=True)]
    score = round(sum(right) * 100 / len(questions))
    passed = score >= _pass_percent(module)
    QuizAttempt.objects.create(
        enrollment=enrollment, module=module, answers=answers, score_percent=score, passed=passed
    )
    enrollment = refresh(enrollment)
    return {
        "score_percent": score,
        "passed": passed,
        "pass_percent": _pass_percent(module),
        "results": [
            {"question": str(q.pk), "right": ok, "correct": q.correct}
            for q, ok in zip(questions, right, strict=True)
        ],
        "enrollment": enrollment,
    }


# --- The end: certificate, badge ----------------------------------------------------------------


def _finished(enrollment: Enrollment) -> None:
    course = enrollment.course
    student = enrollment.user
    certificate = _certificate(enrollment)
    record("academy.completed", enrollment, metadata={"certificate": certificate.code})
    title = course.title
    code = certificate.code
    transaction.on_commit(
        lambda: notify(
            student,
            "academy.certificate_ready",
            {"course": title, "code": code},
            link=f"{LINK}/mes-formations",
        )
    )
    if course.counts_for_badge:
        _badge(student)


def _certificate(enrollment: Enrollment) -> Certificate:
    existing = Certificate.objects.filter(enrollment=enrollment).first()
    if existing is not None:
        return existing
    student = enrollment.user
    name = " ".join(filter(None, (student.first_name, getattr(student, "last_name", ""))))
    for _attempt in range(5):
        code = certificate_code()
        if not Certificate.objects.filter(code=code).exists():
            break
    return Certificate.objects.create(
        enrollment=enrollment,
        code=code,
        holder_name=(name or str(student.phone or student.email or ""))[:120],
        course_title=enrollment.course.title[:120],
        trainer_name=selectors.trainer_name(enrollment.course)[:120],
        issued_at=timezone.now(),
    )


def _badge(user) -> None:
    from apps.pros.models import ProProfile

    pro = ProProfile.objects.filter(user=user, trained_at__isnull=True).first()
    if pro is None:
        return
    pro.trained_at = timezone.now()
    pro.save(update_fields=["trained_at", "updated_at"])
    record("academy.badge", pro)
    transaction.on_commit(lambda: notify(user, "academy.badge_earned", {}, link="/pro"))


def certificate_by_code(code: str) -> Certificate:
    certificate = (
        Certificate.objects.select_related("enrollment__course")
        .filter(code=(code or "").strip().upper())
        .first()
    )
    if certificate is None:
        raise errors.CertificateNotFound()
    return certificate


@transaction.atomic
def revoke(certificate: Certificate, actor, *, reason: str) -> Certificate:
    certificate.revoked_at = timezone.now()
    certificate.revoked_reason = (reason or "")[:200]
    certificate.save(update_fields=["revoked_at", "revoked_reason", "updated_at"])
    record("academy.certificate_revoked", certificate, actor=actor, metadata={"reason": reason})
    return certificate
