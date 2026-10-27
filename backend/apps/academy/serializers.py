"""Inputs and outputs of the academy API. Payload functions build plain dicts; the
serializers describe them for the OpenAPI schema (no business rule here)."""

from __future__ import annotations

import datetime

from django.utils import timezone
from rest_framework import serializers

from apps.core.media.api import MediaPayload
from apps.core.media.services import asset_payload

from . import selectors
from .models import (
    AcademyPass,
    Certificate,
    Course,
    CourseLanguage,
    Enrollment,
    Lesson,
    Level,
    LiveSession,
    Module,
)

# --- Catalogue and course page ------------------------------------------------------------------


class TrainerSerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.CharField(allow_null=True)
    photo = MediaPayload(allow_null=True)
    platform = serializers.BooleanField()
    trained = serializers.BooleanField()


def trainer_payload(course) -> dict:
    pro = course.pro
    if pro is None:
        return {
            "name": "Solange Glow",
            "slug": None,
            "photo": None,
            "platform": True,
            "trained": False,
        }
    photo = pro.photo if pro.photo is not None and pro.photo.is_ready else None
    return {
        "name": pro.display_name,
        "slug": pro.slug,
        "photo": asset_payload(photo),
        "platform": False,
        "trained": pro.is_trained,
    }


class CourseCardSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    slug = serializers.CharField()
    title = serializers.CharField()
    summary = serializers.CharField()
    cover = MediaPayload(allow_null=True)
    trade = serializers.CharField(allow_null=True)
    trade_name = serializers.CharField(allow_null=True)
    level = serializers.ChoiceField(choices=Level.choices)
    language = serializers.ChoiceField(choices=CourseLanguage.choices)
    pricing = serializers.ChoiceField(choices=Course.Pricing.choices)
    price_minor = serializers.IntegerField()
    currency = serializers.CharField()
    duration_seconds = serializers.IntegerField()
    lessons_count = serializers.IntegerField()
    students_count = serializers.IntegerField()
    trainer = TrainerSerializer()
    status = serializers.ChoiceField(choices=Course.Status.choices)


def card_payload(course: Course, lessons_count: int | None = None) -> dict:
    cover = course.cover if course.cover is not None and course.cover.is_ready else None
    if lessons_count is None:
        lessons_count = getattr(course, "lessons_count", None)
    if lessons_count is None:
        lessons_count = Lesson.objects.filter(module__course=course).count()
    return {
        "id": course.pk,
        "slug": course.slug,
        "title": course.title,
        "summary": course.summary,
        "cover": asset_payload(cover),
        "trade": course.trade.key if course.trade_id else None,
        "trade_name": course.trade.name if course.trade_id else None,
        "level": course.level,
        "language": course.language,
        "pricing": course.pricing,
        "price_minor": course.price_minor,
        "currency": course.currency,
        "duration_seconds": course.duration_seconds,
        "lessons_count": lessons_count,
        "students_count": course.students_count,
        "trainer": trainer_payload(course),
        "status": course.status,
    }


class CatalogueQuerySerializer(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True, max_length=80)
    trade = serializers.CharField(required=False, allow_blank=True, max_length=40)
    level = serializers.ChoiceField(choices=Level.choices, required=False)
    language = serializers.ChoiceField(choices=CourseLanguage.choices, required=False)
    pricing = serializers.ChoiceField(choices=Course.Pricing.choices, required=False)
    country = serializers.CharField(required=False, allow_blank=True, max_length=2)
    cursor = serializers.CharField(required=False, allow_blank=True)


class PassOfferSerializer(serializers.Serializer):
    price_minor = serializers.IntegerField(allow_null=True)
    currency = serializers.CharField()
    active = serializers.BooleanField()


class CatalogueSerializer(serializers.Serializer):
    results = CourseCardSerializer(many=True)
    next = serializers.CharField(allow_null=True)
    open = serializers.BooleanField()
    country = serializers.CharField()
    pass_offer = PassOfferSerializer()


def pass_offer(country, user) -> dict:
    return {
        "price_minor": selectors.pass_price(country),
        "currency": selectors.currency_of(country),
        "active": selectors.has_pass(user),
    }


class LessonSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    duration_seconds = serializers.IntegerField()
    is_preview = serializers.BooleanField()
    done = serializers.BooleanField()


class ModuleSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    lessons = LessonSummarySerializer(many=True)
    questions_count = serializers.IntegerField()
    quiz_passed = serializers.BooleanField()


class MyEnrollmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    access = serializers.ChoiceField(choices=Enrollment.Access.choices)
    status = serializers.ChoiceField(choices=Enrollment.Status.choices)
    progress_percent = serializers.IntegerField()
    last_lesson = serializers.UUIDField(allow_null=True)
    started = serializers.BooleanField()
    completed_at = serializers.DateTimeField(allow_null=True)
    certificate = serializers.CharField(allow_null=True)
    can_watch = serializers.BooleanField()
    refund_until = serializers.DateTimeField(allow_null=True)


def enrollment_payload(enrollment: Enrollment | None, user) -> dict | None:
    if enrollment is None:
        return None
    from .services.enrollments import refund_days

    refund_until = None
    payment = enrollment.payment
    if (
        enrollment.access == Enrollment.Access.PURCHASE
        and enrollment.status == Enrollment.Status.ACTIVE
        and enrollment.started_at is None
        and payment is not None
        and payment.status == payment.Status.HELD
        and payment.paid_at is not None
    ):
        until = payment.paid_at + datetime.timedelta(days=refund_days(enrollment.course))
        refund_until = until if until > timezone.now() else None
    certificate = Certificate.objects.filter(enrollment=enrollment).first()
    return {
        "id": enrollment.pk,
        "access": enrollment.access,
        "status": enrollment.status,
        "progress_percent": enrollment.progress_percent,
        "last_lesson": enrollment.last_lesson_id,
        "started": enrollment.started_at is not None,
        "completed_at": enrollment.completed_at,
        "certificate": certificate.code if certificate and certificate.is_valid else None,
        "can_watch": selectors.can_watch(user, enrollment.course, enrollment),
        "refund_until": refund_until,
    }


class CourseDetailSerializer(CourseCardSerializer):
    description = serializers.CharField()
    country = serializers.CharField()
    published_at = serializers.DateTimeField(allow_null=True)
    modules = ModuleSummarySerializer(many=True)
    enrollment = MyEnrollmentSerializer(allow_null=True)
    is_trainer = serializers.BooleanField()
    pass_offer = PassOfferSerializer()
    refund_days = serializers.IntegerField()


def course_detail_payload(course: Course, user) -> dict:
    from .models import LessonProgress, QuizAttempt
    from .services.enrollments import refund_days

    enrollment = selectors.enrollment_of(user, course)
    done, passed = set(), set()
    if enrollment is not None:
        done = set(
            LessonProgress.objects.filter(
                enrollment=enrollment, completed_at__isnull=False
            ).values_list("lesson_id", flat=True)
        )
        passed = set(
            QuizAttempt.objects.filter(enrollment=enrollment, passed=True).values_list(
                "module_id", flat=True
            )
        )
    modules = []
    count = 0
    for module in course.modules.prefetch_related("lessons", "questions"):
        lessons = list(module.lessons.all())
        count += len(lessons)
        modules.append(
            {
                "id": module.pk,
                "title": module.title,
                "lessons": [
                    {
                        "id": lesson.pk,
                        "title": lesson.title,
                        "duration_seconds": lesson.duration_seconds,
                        "is_preview": lesson.is_preview,
                        "done": lesson.pk in done,
                    }
                    for lesson in lessons
                ],
                "questions_count": len(module.questions.all()),
                "quiz_passed": module.pk in passed,
            }
        )
    return {
        **card_payload(course, count),
        "description": course.description,
        "country": course.country.code,
        "published_at": course.published_at,
        "modules": modules,
        "enrollment": enrollment_payload(enrollment, user),
        "is_trainer": selectors.is_trainer(user, course),
        "pass_offer": pass_offer(course.country, user),
        "refund_days": refund_days(course),
    }


class GetCourseSerializer(serializers.Serializer):
    waiver = serializers.BooleanField(required=False, default=False)
    waiver_text = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class GetCourseResultSerializer(serializers.Serializer):
    enrollment = MyEnrollmentSerializer(allow_null=True)
    checkout_url = serializers.CharField(allow_null=True)


# --- Player -------------------------------------------------------------------------------------


class ResourceLinkSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    url = serializers.CharField(allow_null=True)


class VideoLinksSerializer(serializers.Serializer):
    low = serializers.CharField(allow_null=True, required=False)
    medium = serializers.CharField(allow_null=True, required=False)
    poster = serializers.CharField(allow_null=True, required=False)


class LessonPlaybackSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField()
    duration_seconds = serializers.IntegerField()
    course_slug = serializers.CharField()
    course_title = serializers.CharField()
    module_id = serializers.UUIDField()
    module_title = serializers.CharField()
    previous = serializers.UUIDField(allow_null=True)
    next = serializers.UUIDField(allow_null=True)
    quiz_after = serializers.UUIDField(allow_null=True)
    urls = VideoLinksSerializer()
    resources = ResourceLinkSerializer(many=True)
    position_seconds = serializers.IntegerField()
    expires_in = serializers.IntegerField()


def playback_payload(state: dict) -> dict:
    from .services.common import lessons_of

    lesson = state["lesson"]
    module = lesson.module
    course = module.course
    order = list(lessons_of(course).values_list("pk", "module_id"))
    ids = [pk for pk, _module in order]
    index = ids.index(lesson.pk)
    following = order[index + 1] if index + 1 < len(order) else None
    last_of_module = following is None or following[1] != module.pk
    quiz_after = module.pk if last_of_module and module.questions.exists() else None
    return {
        "id": lesson.pk,
        "title": lesson.title,
        "description": lesson.description,
        "duration_seconds": lesson.duration_seconds,
        "course_slug": course.slug,
        "course_title": course.title,
        "module_id": module.pk,
        "module_title": module.title,
        "previous": ids[index - 1] if index > 0 else None,
        "next": following[0] if following else None,
        "quiz_after": quiz_after,
        "urls": state["urls"],
        "resources": state["resources"],
        "position_seconds": state["position_seconds"],
        "expires_in": state["expires_in"],
    }


class PositionSerializer(serializers.Serializer):
    seconds = serializers.IntegerField(min_value=0, max_value=24 * 3600)
    ended = serializers.BooleanField(required=False, default=False)


class ProgressSerializer(serializers.Serializer):
    progress_percent = serializers.IntegerField()
    completed = serializers.BooleanField()
    certificate = serializers.CharField(allow_null=True)


def progress_payload(enrollment: Enrollment) -> dict:
    certificate = Certificate.objects.filter(enrollment=enrollment).first()
    return {
        "progress_percent": enrollment.progress_percent,
        "completed": enrollment.completed_at is not None,
        "certificate": certificate.code if certificate else None,
    }


class QuizQuestionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    text = serializers.CharField()
    choices = serializers.ListField(child=serializers.CharField())


class QuizSerializer(serializers.Serializer):
    module_id = serializers.UUIDField()
    module_title = serializers.CharField()
    course_slug = serializers.CharField()
    questions = QuizQuestionSerializer(many=True)
    unlocked = serializers.BooleanField()
    passed = serializers.BooleanField()
    last_score = serializers.IntegerField(allow_null=True)
    pass_percent = serializers.IntegerField()


def quiz_payload(state: dict) -> dict:
    module = state["module"]
    return {
        "module_id": module.pk,
        "module_title": module.title,
        "course_slug": module.course.slug,
        "questions": [
            {"id": q.pk, "text": q.text, "choices": q.choices} for q in state["questions"]
        ],
        "unlocked": state["unlocked"],
        "passed": state["passed"],
        "last_score": state["last_score"],
        "pass_percent": state["pass_percent"],
    }


class AnswersSerializer(serializers.Serializer):
    answers = serializers.ListField(child=serializers.IntegerField(min_value=0, max_value=3))


class QuizResultLineSerializer(serializers.Serializer):
    question = serializers.UUIDField()
    right = serializers.BooleanField()
    correct = serializers.IntegerField()


class QuizResultSerializer(serializers.Serializer):
    score_percent = serializers.IntegerField()
    passed = serializers.BooleanField()
    pass_percent = serializers.IntegerField()
    results = QuizResultLineSerializer(many=True)
    progress = ProgressSerializer()


# --- My courses, certificates, pass -------------------------------------------------------------


class MyCourseSerializer(serializers.Serializer):
    course = CourseCardSerializer()
    enrollment = MyEnrollmentSerializer()


class AcademyPassSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=AcademyPass.Status.choices)
    active = serializers.BooleanField()
    current_period_end = serializers.DateTimeField(allow_null=True)
    cancel_at_period_end = serializers.BooleanField()
    payment_due = serializers.BooleanField()
    price_minor = serializers.IntegerField(allow_null=True)
    currency = serializers.CharField()


def pass_payload(user) -> dict:
    found = selectors.pass_of(user)
    country = user.country
    due = bool(
        found
        and found.renewal_payment_id
        and found.renewal_payment.status == found.renewal_payment.Status.PENDING_PAYMENT
    )
    return {
        "status": found.status if found else AcademyPass.Status.ENDED,
        "active": selectors.has_pass(user),
        "current_period_end": found.current_period_end if found else None,
        "cancel_at_period_end": found.cancel_at_period_end if found else False,
        "payment_due": due,
        "price_minor": selectors.pass_price(country) if country else None,
        "currency": selectors.currency_of(country) if country else "XOF",
    }


class MyAcademySerializer(serializers.Serializer):
    courses = MyCourseSerializer(many=True)
    academy_pass = AcademyPassSerializer()


class CertificateCheckSerializer(serializers.Serializer):
    code = serializers.CharField()
    valid = serializers.BooleanField()
    holder_name = serializers.CharField()
    course_title = serializers.CharField()
    course_slug = serializers.CharField(allow_null=True)
    trainer_name = serializers.CharField()
    issued_at = serializers.DateTimeField()
    revoked_at = serializers.DateTimeField(allow_null=True)


def certificate_payload(certificate: Certificate) -> dict:
    course = certificate.enrollment.course
    return {
        "code": certificate.code,
        "valid": certificate.is_valid,
        "holder_name": certificate.holder_name,
        "course_title": certificate.course_title,
        "course_slug": course.slug if course.status == Course.Status.PUBLISHED else None,
        "trainer_name": certificate.trainer_name,
        "issued_at": certificate.issued_at,
        "revoked_at": certificate.revoked_at,
    }


# --- Lives --------------------------------------------------------------------------------------


class LiveSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField()
    language = serializers.ChoiceField(choices=CourseLanguage.choices)
    starts_at = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField()
    capacity = serializers.IntegerField()
    places_left = serializers.IntegerField()
    status = serializers.ChoiceField(choices=LiveSession.Status.choices)
    trainer_name = serializers.CharField()
    course_slug = serializers.CharField(allow_null=True)
    course_title = serializers.CharField(allow_null=True)
    registered = serializers.BooleanField()


def live_payload(live: LiveSession, registered: bool) -> dict:
    return {
        "id": live.pk,
        "title": live.title,
        "description": live.description,
        "language": live.language,
        "starts_at": live.starts_at,
        "duration_minutes": live.duration_minutes,
        "capacity": live.capacity,
        "places_left": max(0, live.capacity - live.registered_count),
        "status": live.status,
        "trainer_name": live.pro.display_name if live.pro_id else "Solange Glow",
        "course_slug": live.course.slug if live.course_id else None,
        "course_title": live.course.title if live.course_id else None,
        "registered": registered,
    }


class LivesSerializer(serializers.Serializer):
    results = LiveSerializer(many=True)
    open = serializers.BooleanField()


class LiveRoomSerializer(serializers.Serializer):
    live = LiveSerializer()
    registered = serializers.BooleanField()
    host = serializers.BooleanField()
    opens_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    open = serializers.BooleanField()
    seconds_left = serializers.IntegerField()
    broadcast_ready = serializers.BooleanField()


class JoinSerializer(serializers.Serializer):
    url = serializers.CharField()


# --- Trainer space ------------------------------------------------------------------------------


class CourseInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120, required=False)
    summary = serializers.CharField(max_length=200, required=False, allow_blank=True)
    description = serializers.CharField(max_length=4000, required=False, allow_blank=True)
    trade = serializers.CharField(max_length=40, required=False, allow_blank=True)
    level = serializers.ChoiceField(choices=Level.choices, required=False)
    language = serializers.ChoiceField(choices=CourseLanguage.choices, required=False)
    pricing = serializers.ChoiceField(choices=Course.Pricing.choices, required=False)
    price_minor = serializers.IntegerField(min_value=0, required=False)
    cover_id = serializers.UUIDField(required=False, allow_null=True)


class NewCourseSerializer(CourseInputSerializer):
    title = serializers.CharField(max_length=120)
    platform = serializers.BooleanField(required=False, default=False)
    country = serializers.CharField(max_length=2, required=False, allow_blank=True)


class TitleSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120)


class LessonInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120)
    description = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    video_id = serializers.UUIDField(required=False, allow_null=True)
    is_preview = serializers.BooleanField(required=False, default=False)


class CourseResourceInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120)
    file_id = serializers.UUIDField()


class QuestionInputSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=300)
    choices = serializers.ListField(child=serializers.CharField(max_length=200), max_length=4)
    correct = serializers.IntegerField(min_value=0, max_value=3)


class StudioResourceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    file = MediaPayload(allow_null=True)


class StudioLessonSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField()
    duration_seconds = serializers.IntegerField()
    is_preview = serializers.BooleanField()
    video = MediaPayload(allow_null=True)
    resources = StudioResourceSerializer(many=True)


class StudioQuestionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    text = serializers.CharField()
    choices = serializers.ListField(child=serializers.CharField())
    correct = serializers.IntegerField()


class StudioModuleSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    lessons = StudioLessonSerializer(many=True)
    questions = StudioQuestionSerializer(many=True)


class CourseStatsSerializer(serializers.Serializer):
    students = serializers.IntegerField()
    finished = serializers.IntegerField()
    completion_percent = serializers.IntegerField()
    earned_minor = serializers.IntegerField()


class StudioCourseSerializer(CourseCardSerializer):
    description = serializers.CharField()
    country = serializers.CharField()
    review_note = serializers.CharField()
    needs_recheck = serializers.BooleanField()
    modules = StudioModuleSerializer(many=True)
    stats = CourseStatsSerializer()
    price_min = serializers.IntegerField()
    price_max = serializers.IntegerField()


def _module_payload(module: Module) -> dict:
    return {
        "id": module.pk,
        "title": module.title,
        "lessons": [
            {
                "id": lesson.pk,
                "title": lesson.title,
                "description": lesson.description,
                "duration_seconds": lesson.duration_seconds,
                "is_preview": lesson.is_preview,
                "video": asset_payload(lesson.video),
                "resources": [
                    {"id": r.pk, "title": r.title, "file": asset_payload(r.file)}
                    for r in lesson.resources.select_related("file")
                ],
            }
            for lesson in module.lessons.select_related("video")
        ],
        "questions": [
            {"id": q.pk, "text": q.text, "choices": q.choices, "correct": q.correct}
            for q in module.questions.all()
        ],
    }


def studio_course_payload(course: Course) -> dict:
    from .stats import course_stats

    low, high = selectors.price_limits(course.country)
    modules = [_module_payload(m) for m in course.modules.all()]
    count = sum(len(m["lessons"]) for m in modules)
    card = card_payload(course, count)
    card["cover"] = asset_payload(course.cover)  # the trainer sees it while it is processed
    return {
        **card,
        "description": course.description,
        "country": course.country.code,
        "review_note": course.review_note,
        "needs_recheck": course.needs_recheck,
        "modules": modules,
        "stats": course_stats([course])[course.pk],
        "price_min": low,
        "price_max": high,
    }


class StudioCardSerializer(CourseCardSerializer):
    stats = CourseStatsSerializer()
    review_note = serializers.CharField()


class StudioSerializer(serializers.Serializer):
    courses = StudioCardSerializer(many=True)
    lives = LiveSerializer(many=True)
    can_platform = serializers.BooleanField()
    is_pro = serializers.BooleanField()
    open = serializers.BooleanField()
    lives_open = serializers.BooleanField()


class LiveInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120)
    description = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    language = serializers.ChoiceField(choices=CourseLanguage.choices, required=False)
    starts_at = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField()
    capacity = serializers.IntegerField()
    course_id = serializers.UUIDField(required=False, allow_null=True)
    platform = serializers.BooleanField(required=False, default=False)
    country = serializers.CharField(max_length=2, required=False, allow_blank=True)
