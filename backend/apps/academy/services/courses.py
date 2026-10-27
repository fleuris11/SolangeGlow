"""A trainer writes a course step by step; the team reviews the courses of the pros before
they are published (the platform's own courses are published at once)."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from django.utils.translation import get_language

from apps.core.audit.services import record
from apps.core.media.models import MediaAsset
from apps.core.models import Country
from apps.core.money import Money
from apps.notifications.services import notify
from apps.pros.models import Trade

from .. import errors, selectors
from ..models import Course, CourseLanguage, Lesson, Level, Module, Question, Resource
from .common import LINK, lessons_of, refresh_duration, require_open, unique_slug

C = Course.Status
EDITABLE = (C.DRAFT, C.REJECTED, C.PUBLISHED)
COURSE_FIELDS = ("title", "summary", "description", "level", "language", "pricing", "price_minor")


def _owner_pro(user):
    from apps.pros.services import get_pro

    return get_pro(user)


def _check_trainer(user, course: Course) -> None:
    if not selectors.is_trainer(user, course):
        raise errors.NotTrainer()


def _media(user, media_id, purpose: str) -> MediaAsset | None:
    if not media_id:
        return None
    asset = MediaAsset.objects.filter(pk=media_id, purpose=purpose).first()
    if asset is None or (asset.owner_id != user.pk):
        raise errors.InvalidLesson()
    return asset


def _validate(course: Course, values: dict) -> None:
    title = (values.get("title", course.title) or "").strip()
    if not title or len(title) > 120:
        raise errors.InvalidCourse()
    if values.get("level", course.level) not in Level.values:
        raise errors.InvalidCourse()
    if values.get("language", course.language) not in CourseLanguage.values:
        raise errors.InvalidCourse()
    pricing = values.get("pricing", course.pricing)
    price = values.get("price_minor", course.price_minor)
    if pricing not in Course.Pricing.values or type(price) is not int:
        raise errors.InvalidCourse()
    if pricing == Course.Pricing.PASS and course.pro_id:
        raise errors.PassOnlyForPlatform()
    if pricing == Course.Pricing.PAID:
        low, high = selectors.price_limits(course.country)
        if not low <= price <= high:
            language = get_language() or "fr"
            raise errors.InvalidPrice(
                details={
                    "min": Money(low, course.currency).format(language),
                    "max": Money(high, course.currency).format(language),
                }
            )


def _apply(course: Course, values: dict, user) -> None:
    for field in COURSE_FIELDS:
        if field in values and values[field] is not None:
            setattr(course, field, values[field].strip() if field == "title" else values[field])
    if course.pricing != Course.Pricing.PAID:
        course.price_minor = 0
    if "trade" in values:
        key = values["trade"]
        course.trade = Trade.objects.filter(key=key, is_active=True).first() if key else None
        if key and course.trade is None:
            raise errors.InvalidCourse()
    if "cover_id" in values:
        course.cover = _media(user, values["cover_id"], "course_cover")


@transaction.atomic
def create_course(user, *, platform: bool = False, country: str = "", **values) -> Course:
    """A new draft. A pro writes for her showcase; the team writes for the platform."""
    if platform:
        if not selectors.can_manage_platform(user):
            raise errors.NotTrainer()
        place = Country.objects.select_related("default_currency").filter(code=country).first()
        if place is None:
            raise errors.InvalidCourse()
        pro = None
    else:
        pro = _owner_pro(user)
        place = pro.country
        if place is None:
            raise errors.InvalidCourse()
    require_open(place)
    course = Course(
        pro=pro,
        author=user,
        country=place,
        currency=(pro.currency if pro and pro.currency else selectors.currency_of(place)),
    )
    _validate(course, values)
    _apply(course, values, user)
    course.slug = unique_slug(course.title)
    course.save()
    record("academy.course_created", course, actor=user)
    return course


@transaction.atomic
def update_course(course: Course, user, **values) -> Course:
    course = Course.objects.select_for_update().get(pk=course.pk)
    _check_trainer(user, course)
    if course.status not in EDITABLE:
        raise errors.NotEditable()
    _validate(course, values)
    _apply(course, values, user)
    _changed(course)
    course.save()
    record("academy.course_changed", course, actor=user)
    return course


def _changed(course: Course) -> None:
    """A pro changes a published course: it stays online, the team looks at it again."""
    if course.status == C.PUBLISHED and course.pro_id:
        course.needs_recheck = True


def _touch(course: Course) -> None:
    if course.status == C.IN_REVIEW:
        raise errors.NotEditable()
    if course.status == C.PUBLISHED and course.pro_id and not course.needs_recheck:
        course.needs_recheck = True
        course.save(update_fields=["needs_recheck", "updated_at"])


def _no_students(course: Course) -> None:
    if course.enrollments.exists():
        raise errors.NotEditable()


# --- Modules, lessons, resources, quiz ----------------------------------------------------------


def save_module(course: Course, user, *, module_id=None, title: str) -> Module:
    _check_trainer(user, course)
    _touch(course)
    title = (title or "").strip()
    if not title or len(title) > 120:
        raise errors.InvalidCourse()
    if module_id:
        module = Module.objects.filter(pk=module_id, course=course).first()
        if module is None:
            raise errors.CourseNotFound()
        module.title = title
        module.save(update_fields=["title", "updated_at"])
        return module
    return Module.objects.create(course=course, title=title, position=course.modules.count())


def delete_module(module: Module, user) -> None:
    course = module.course
    _check_trainer(user, course)
    _touch(course)
    _no_students(course)
    module.delete()
    refresh_duration(course)


def save_lesson(
    module: Module,
    user,
    *,
    lesson_id=None,
    title: str,
    description: str = "",
    video_id=None,
    is_preview: bool = False,
) -> Lesson:
    course = module.course
    _check_trainer(user, course)
    _touch(course)
    title = (title or "").strip()
    if not title or len(title) > 120 or len(description or "") > 2000:
        raise errors.InvalidLesson()
    lesson = None
    if lesson_id:
        lesson = Lesson.objects.filter(pk=lesson_id, module__course=course).first()
        if lesson is None:
            raise errors.CourseNotFound()
    else:
        lesson = Lesson(module=module, position=module.lessons.count())
    lesson.title = title
    lesson.description = description or ""
    lesson.is_preview = bool(is_preview)
    if video_id is not None:
        video = _media(user, video_id, "lesson_video")
        if video is None or video.status in (MediaAsset.Status.REJECTED, MediaAsset.Status.FAILED):
            raise errors.InvalidLesson()
        lesson.video = video
        lesson.duration_seconds = int(video.duration_seconds or 0)
    if lesson.video_id is None:
        raise errors.InvalidLesson()
    lesson.save()
    refresh_duration(course)
    return lesson


def delete_lesson(lesson: Lesson, user) -> None:
    course = lesson.module.course
    _check_trainer(user, course)
    _touch(course)
    _no_students(course)
    lesson.delete()
    refresh_duration(course)


def add_resource(lesson: Lesson, user, *, title: str, file_id) -> Resource:
    course = lesson.module.course
    _check_trainer(user, course)
    _touch(course)
    title = (title or "").strip()
    asset = _media(user, file_id, "course_resource")
    if not title or len(title) > 120 or asset is None:
        raise errors.InvalidLesson()
    return Resource.objects.create(
        lesson=lesson, title=title, file=asset, position=lesson.resources.count()
    )


def delete_resource(resource: Resource, user) -> None:
    course = resource.lesson.module.course
    _check_trainer(user, course)
    _touch(course)
    resource.delete()


def save_question(
    module: Module, user, *, question_id=None, text: str, choices: list, correct: int
) -> Question:
    course = module.course
    _check_trainer(user, course)
    _touch(course)
    text = (text or "").strip()
    answers = [str(c).strip()[:200] for c in (choices or [])]
    if (
        not text
        or len(text) > 300
        or not 2 <= len(answers) <= 4
        or not all(answers)
        or type(correct) is not int
        or not 0 <= correct < len(answers)
    ):
        raise errors.InvalidQuestion()
    if question_id:
        question = Question.objects.filter(pk=question_id, module=module).first()
        if question is None:
            raise errors.CourseNotFound()
    else:
        question = Question(module=module, position=module.questions.count())
    question.text, question.choices, question.correct = text, answers, correct
    question.save()
    return question


def delete_question(question: Question, user) -> None:
    course = question.module.course
    _check_trainer(user, course)
    _touch(course)
    question.delete()


# --- Review and publication ---------------------------------------------------------------------


def _ready(course: Course) -> None:
    lessons = list(lessons_of(course).select_related("video"))
    if not course.title or not lessons:
        raise errors.NotReady()
    if any(lesson.video is None or not lesson.video.is_ready for lesson in lessons):
        raise errors.NotReady()
    if course.modules.filter(lessons__isnull=True).exists():
        raise errors.NotReady()


@transaction.atomic
def submit(course: Course, user) -> Course:
    """A pro sends her course to the team; the platform publishes its own at once."""
    course = Course.objects.select_for_update().get(pk=course.pk)
    _check_trainer(user, course)
    if course.status not in (C.DRAFT, C.REJECTED):
        raise errors.InvalidTransition()
    _ready(course)
    refresh_duration(course)
    if course.pro_id is None:
        return _publish(course, user)
    course.status = C.IN_REVIEW
    course.submitted_at = timezone.now()
    course.review_note = ""
    course.save()
    record("academy.course_submitted", course, actor=user)
    return course


def _publish(course: Course, actor) -> Course:
    course.status = C.PUBLISHED
    course.published_at = course.published_at or timezone.now()
    course.needs_recheck = False
    course.save()
    record("academy.course_published", course, actor=actor)
    return course


@transaction.atomic
def approve(course: Course, actor) -> Course:
    course = (
        Course.objects.select_for_update(of=("self",)).select_related("pro__user").get(pk=course.pk)
    )
    if course.status == C.PUBLISHED and course.needs_recheck:
        course.needs_recheck = False
        course.save(update_fields=["needs_recheck", "updated_at"])
        record("academy.course_rechecked", course, actor=actor)
        return course
    if course.status != C.IN_REVIEW:
        raise errors.InvalidTransition()
    _publish(course, actor)
    if course.pro_id:
        user = course.pro.user
        title, slug = course.title, course.slug
        transaction.on_commit(
            lambda: notify(
                user, "academy.course_published", {"course": title}, link=f"{LINK}/{slug}"
            )
        )
    return course


@transaction.atomic
def reject(course: Course, actor, *, note: str) -> Course:
    course = (
        Course.objects.select_for_update(of=("self",)).select_related("pro__user").get(pk=course.pk)
    )
    if course.status not in (C.IN_REVIEW, C.PUBLISHED) or not (note or "").strip():
        raise errors.InvalidTransition()
    course.status = C.REJECTED
    course.review_note = note.strip()[:2000]
    course.needs_recheck = False
    course.save()
    record("academy.course_rejected", course, actor=actor, metadata={"note": course.review_note})
    if course.pro_id:
        user = course.pro.user
        title = course.title
        transaction.on_commit(
            lambda: notify(
                user,
                "academy.course_rejected",
                {"course": title, "note": course.review_note},
                link="/pro/academy",
            )
        )
    return course


@transaction.atomic
def archive(course: Course, user) -> Course:
    """Out of the catalogue; the students keep what they have."""
    course = Course.objects.select_for_update().get(pk=course.pk)
    _check_trainer(user, course)
    if course.status == C.ARCHIVED:
        return course
    course.status = C.ARCHIVED
    course.save(update_fields=["status", "updated_at"])
    record("academy.course_archived", course, actor=user)
    return course
