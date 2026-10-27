from __future__ import annotations

from django.db.models import Count
from django.http import HttpResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttling import SettingRateThrottle
from apps.accounts.views import client_ip
from apps.accounts.views_base import OptionalAuthView
from apps.core.providers.base import ProviderNotConfigured
from apps.glowpro.serializers import CheckoutUrlSerializer
from apps.pros.models import ProProfile
from apps.pros.search import decode_cursor, encode_cursor

from . import certificate as certificate_pdf
from . import errors, selectors, stats
from . import serializers as s
from .live import live_provider
from .models import (
    Certificate,
    Course,
    Enrollment,
    Lesson,
    LiveRegistration,
    LiveSession,
    Module,
    Question,
    Resource,
)
from .services import courses, enrollments, lives, passes, progress

PAGE = 20


def _country(request, wanted: str = "") -> str:
    if wanted:
        return wanted.upper()
    user = request.user
    if user.is_authenticated and user.country_id:
        return user.country.code
    return "BJ"


class AcademyView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "academy"


class PublicAcademyView(OptionalAuthView):
    throttle_scope = "academy"


# --- Catalogue and course page ------------------------------------------------------------------


class CatalogueView(PublicAcademyView):
    @extend_schema(
        operation_id="academy_catalogue",
        tags=["academy"],
        parameters=[s.CatalogueQuerySerializer],
        responses=s.CatalogueSerializer,
    )
    def get(self, request):
        query = s.CatalogueQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        country = _country(request, data.get("country", ""))
        offset = decode_cursor(data.get("cursor"))
        rows = list(
            selectors.catalogue(
                country,
                q=data.get("q", ""),
                trade=data.get("trade", ""),
                level=data.get("level", ""),
                language=data.get("language", ""),
                pricing=data.get("pricing", ""),
            ).annotate(lessons_count=Count("modules__lessons"))[offset : offset + PAGE + 1]
        )
        return Response(
            {
                "results": [s.card_payload(course) for course in rows[:PAGE]],
                "next": encode_cursor(offset + PAGE) if len(rows) > PAGE else None,
                "open": selectors.is_open(country),
                "country": country,
                "pass_offer": s.pass_offer(country, request.user),
            }
        )


class CourseView(PublicAcademyView):
    @extend_schema(tags=["academy"], responses=s.CourseDetailSerializer)
    def get(self, request, slug):
        course = selectors.course_by_slug(slug, request.user)
        return Response(s.course_detail_payload(course, request.user))


class GetCourseView(AcademyView):
    @extend_schema(
        tags=["academy"], request=s.GetCourseSerializer, responses=s.GetCourseResultSerializer
    )
    def post(self, request, slug):
        data = s.GetCourseSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        course = selectors.course_by_slug(slug, request.user)
        enrollment, checkout_url = enrollments.get_course(
            request.user,
            course,
            waiver=data.validated_data["waiver"],
            waiver_text=data.validated_data.get("waiver_text", ""),
            ip=client_ip(request),
        )
        payload = None if checkout_url else s.enrollment_payload(enrollment, request.user)
        return Response({"enrollment": payload, "checkout_url": checkout_url})


class RefundView(AcademyView):
    @extend_schema(tags=["academy"], request=None, responses=s.MyEnrollmentSerializer)
    def post(self, request, enrollment_id):
        enrollment = Enrollment.objects.filter(pk=enrollment_id, user=request.user).first()
        if enrollment is None:
            raise errors.NotEnrolled()
        enrollment = enrollments.refund(enrollment, request.user)
        return Response(s.enrollment_payload(enrollment, request.user))


# --- Player and quiz ----------------------------------------------------------------------------


class LessonView(PublicAcademyView):
    @extend_schema(tags=["academy"], responses=s.LessonPlaybackSerializer)
    def get(self, request, lesson_id):
        lesson = progress.find_lesson(lesson_id, request.user)
        return Response(s.playback_payload(progress.playback(request.user, lesson)))


class PositionView(AcademyView):
    @extend_schema(tags=["academy"], request=s.PositionSerializer, responses=s.ProgressSerializer)
    def post(self, request, lesson_id):
        data = s.PositionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        lesson = progress.find_lesson(lesson_id, request.user)
        enrollment = progress.save_position(
            request.user,
            lesson,
            seconds=data.validated_data["seconds"],
            ended=data.validated_data["ended"],
        )
        return Response(s.progress_payload(enrollment))


def _module(module_id) -> Module:
    module = (
        Module.objects.select_related("course__country", "course__pro").filter(pk=module_id).first()
    )
    if module is None:
        raise errors.CourseNotFound()
    return module


class QuizView(AcademyView):
    @extend_schema(tags=["academy"], responses=s.QuizSerializer)
    def get(self, request, module_id):
        return Response(s.quiz_payload(progress.quiz_of(request.user, _module(module_id))))

    @extend_schema(tags=["academy"], request=s.AnswersSerializer, responses=s.QuizResultSerializer)
    def post(self, request, module_id):
        data = s.AnswersSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        result = progress.submit_quiz(
            request.user, _module(module_id), data.validated_data["answers"]
        )
        enrollment = result.pop("enrollment")
        return Response({**result, "progress": s.progress_payload(enrollment)})


# --- My courses, certificates, pass -------------------------------------------------------------


class MyAcademyView(AcademyView):
    @extend_schema(tags=["academy"], responses=s.MyAcademySerializer)
    def get(self, request):
        rows = (
            Enrollment.objects.filter(user=request.user)
            .exclude(status=Enrollment.Status.WAITING)
            .select_related("course__pro__user", "course__cover", "course__trade", "payment")
            .annotate(lessons_count=Count("course__modules__lessons"))
            .order_by("-updated_at")
        )
        courses_list = []
        for enrollment in rows:
            courses_list.append(
                {
                    "course": s.card_payload(enrollment.course, enrollment.lessons_count),
                    "enrollment": s.enrollment_payload(enrollment, request.user),
                }
            )
        return Response({"courses": courses_list, "academy_pass": s.pass_payload(request.user)})


class CertificateCheckView(PublicAcademyView):
    @extend_schema(tags=["academy"], responses=s.CertificateCheckSerializer)
    def get(self, request, code):
        return Response(s.certificate_payload(progress.certificate_by_code(code)))


class CertificatePdfView(AcademyView):
    @extend_schema(
        tags=["academy"],
        responses={(200, "application/pdf"): OpenApiResponse(description="PDF")},
    )
    def get(self, request, code):
        certificate = (
            Certificate.objects.select_related("enrollment")
            .filter(code=(code or "").upper(), enrollment__user=request.user)
            .first()
        )
        if certificate is None or not certificate.is_valid:
            raise errors.CertificateNotFound()
        language = (request.LANGUAGE_CODE or "fr")[:2]
        content = certificate_pdf.render(certificate, language)
        response = HttpResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="certificat-{certificate.code}.pdf"'
        return response


class PassView(AcademyView):
    @extend_schema(tags=["academy"], responses=s.AcademyPassSerializer)
    def get(self, request):
        return Response(s.pass_payload(request.user))


class PassSubscribeView(AcademyView):
    @extend_schema(tags=["academy"], request=None, responses=CheckoutUrlSerializer)
    def post(self, request):
        payment = passes.subscribe(request.user)
        return Response({"checkout_url": payment.checkout_url})


class PassCancelView(AcademyView):
    @extend_schema(tags=["academy"], request=None, responses=s.AcademyPassSerializer)
    def post(self, request):
        passes.cancel(request.user)
        return Response(s.pass_payload(request.user))


# --- Lives --------------------------------------------------------------------------------------


def _registered_ids(user, live_ids) -> set:
    if not user.is_authenticated:
        return set()
    return set(
        LiveRegistration.objects.filter(user=user, live_id__in=live_ids).values_list(
            "live_id", flat=True
        )
    )


class LivesView(PublicAcademyView):
    @extend_schema(operation_id="academy_lives_list", tags=["academy"], responses=s.LivesSerializer)
    def get(self, request):
        country = _country(request, request.query_params.get("country", ""))
        rows = list(selectors.upcoming_lives(country)[:50])
        mine = _registered_ids(request.user, [live.pk for live in rows])
        return Response(
            {
                "results": [s.live_payload(live, live.pk in mine) for live in rows],
                "open": selectors.is_open(country) and selectors.lives_open(country),
            }
        )


def _broadcast_ready() -> bool:
    try:
        live_provider()
    except ProviderNotConfigured:  # the room says « coming soon »
        return False
    return True


class LiveRoomView(AcademyView):
    @extend_schema(tags=["academy"], responses=s.LiveRoomSerializer)
    def get(self, request, live_id):
        live = lives.get_live(live_id)
        state = lives.room(request.user, live)
        registered = state["registered"]
        return Response(
            {
                **state,
                "live": s.live_payload(live, registered),
                "broadcast_ready": _broadcast_ready(),
            }
        )


class LiveRegisterView(AcademyView):
    @extend_schema(tags=["academy"], request=None, responses=s.LiveSerializer)
    def post(self, request, live_id):
        live = lives.get_live(live_id)
        lives.register(request.user, live)
        return Response(s.live_payload(lives.get_live(live_id), True))

    @extend_schema(tags=["academy"], request=None, responses=s.LiveSerializer)
    def delete(self, request, live_id):
        live = lives.get_live(live_id)
        lives.unregister(request.user, live)
        return Response(s.live_payload(lives.get_live(live_id), False))


class LiveJoinView(AcademyView):
    @extend_schema(tags=["academy"], request=None, responses=s.JoinSerializer)
    def post(self, request, live_id):
        return Response({"url": lives.join(request.user, lives.get_live(live_id))})


# --- Trainer space ------------------------------------------------------------------------------


def _studio_course(request, course_id) -> Course:
    course = (
        Course.objects.select_related("pro__user", "country", "cover", "trade")
        .filter(pk=course_id)
        .first()
    )
    if course is None or not selectors.is_trainer(request.user, course):
        raise errors.CourseNotFound()
    return course


def _studio(course: Course) -> Response:
    course.refresh_from_db()
    return Response(s.studio_course_payload(course))


class StudioView(AcademyView):
    @extend_schema(tags=["academy"], responses=s.StudioSerializer)
    def get(self, request):
        user = request.user
        pro = ProProfile.objects.filter(user=user).select_related("country").first()
        platform = selectors.can_manage_platform(user)
        rows = stats.trainer_courses(user)
        if platform:
            rows += stats.trainer_courses(user, platform=True)
        numbers = stats.course_stats(rows)
        lives_rows = LiveSession.objects.filter(author=user).select_related("pro", "course")
        country = pro.country if pro and pro.country_id else (user.country or "BJ")
        return Response(
            {
                "courses": [
                    {
                        **s.card_payload(course),
                        "stats": numbers[course.pk],
                        "review_note": course.review_note,
                    }
                    for course in rows
                ],
                "lives": [
                    s.live_payload(live, False) for live in lives_rows.order_by("-starts_at")[:20]
                ],
                "can_platform": platform,
                "is_pro": pro is not None,
                "open": selectors.is_open(country),
                "lives_open": selectors.lives_open(country),
            }
        )


class StudioCoursesView(AcademyView):
    @extend_schema(
        tags=["academy"], request=s.NewCourseSerializer, responses=s.StudioCourseSerializer
    )
    def post(self, request):
        data = s.NewCourseSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = dict(data.validated_data)
        course = courses.create_course(
            request.user,
            platform=values.pop("platform", False),
            country=values.pop("country", ""),
            **values,
        )
        return _studio(course)


class StudioCourseView(AcademyView):
    @extend_schema(tags=["academy"], responses=s.StudioCourseSerializer)
    def get(self, request, course_id):
        return _studio(_studio_course(request, course_id))

    @extend_schema(
        tags=["academy"], request=s.CourseInputSerializer, responses=s.StudioCourseSerializer
    )
    def patch(self, request, course_id):
        data = s.CourseInputSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        course = courses.update_course(
            _studio_course(request, course_id), request.user, **data.validated_data
        )
        return _studio(course)


class StudioSubmitView(AcademyView):
    @extend_schema(tags=["academy"], request=None, responses=s.StudioCourseSerializer)
    def post(self, request, course_id):
        return _studio(courses.submit(_studio_course(request, course_id), request.user))


class StudioArchiveView(AcademyView):
    @extend_schema(tags=["academy"], request=None, responses=s.StudioCourseSerializer)
    def post(self, request, course_id):
        return _studio(courses.archive(_studio_course(request, course_id), request.user))


class StudioModulesView(AcademyView):
    @extend_schema(tags=["academy"], request=s.TitleSerializer, responses=s.StudioCourseSerializer)
    def post(self, request, course_id):
        data = s.TitleSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        course = _studio_course(request, course_id)
        courses.save_module(course, request.user, title=data.validated_data["title"])
        return _studio(course)


def _studio_module(request, module_id) -> Module:
    module = (
        Module.objects.select_related("course__pro__user", "course__country")
        .filter(pk=module_id)
        .first()
    )
    if module is None or not selectors.is_trainer(request.user, module.course):
        raise errors.CourseNotFound()
    return module


class StudioModuleView(AcademyView):
    @extend_schema(tags=["academy"], request=s.TitleSerializer, responses=s.StudioCourseSerializer)
    def patch(self, request, module_id):
        data = s.TitleSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        module = _studio_module(request, module_id)
        courses.save_module(
            module.course, request.user, module_id=module.pk, title=data.validated_data["title"]
        )
        return _studio(module.course)

    @extend_schema(tags=["academy"], request=None, responses={200: s.StudioCourseSerializer})
    def delete(self, request, module_id):
        module = _studio_module(request, module_id)
        course = module.course
        courses.delete_module(module, request.user)
        return _studio(course)


class StudioLessonsView(AcademyView):
    @extend_schema(
        tags=["academy"], request=s.LessonInputSerializer, responses=s.StudioCourseSerializer
    )
    def post(self, request, module_id):
        data = s.LessonInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        module = _studio_module(request, module_id)
        courses.save_lesson(module, request.user, **data.validated_data)
        return _studio(module.course)


def _studio_lesson(request, lesson_id) -> Lesson:
    lesson = (
        Lesson.objects.select_related("module__course__pro__user", "module__course__country")
        .filter(pk=lesson_id)
        .first()
    )
    if lesson is None or not selectors.is_trainer(request.user, lesson.module.course):
        raise errors.CourseNotFound()
    return lesson


class StudioLessonView(AcademyView):
    @extend_schema(
        tags=["academy"], request=s.LessonInputSerializer, responses=s.StudioCourseSerializer
    )
    def patch(self, request, lesson_id):
        data = s.LessonInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        lesson = _studio_lesson(request, lesson_id)
        values = dict(data.validated_data)
        if "video_id" not in request.data:
            values.pop("video_id", None)  # unchanged video
        courses.save_lesson(lesson.module, request.user, lesson_id=lesson.pk, **values)
        return _studio(lesson.module.course)

    @extend_schema(tags=["academy"], request=None, responses={200: s.StudioCourseSerializer})
    def delete(self, request, lesson_id):
        lesson = _studio_lesson(request, lesson_id)
        course = lesson.module.course
        courses.delete_lesson(lesson, request.user)
        return _studio(course)


class StudioResourcesView(AcademyView):
    @extend_schema(
        tags=["academy"],
        request=s.CourseResourceInputSerializer,
        responses=s.StudioCourseSerializer,
    )
    def post(self, request, lesson_id):
        data = s.CourseResourceInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        lesson = _studio_lesson(request, lesson_id)
        courses.add_resource(lesson, request.user, **data.validated_data)
        return _studio(lesson.module.course)


class StudioResourceView(AcademyView):
    @extend_schema(tags=["academy"], request=None, responses={200: s.StudioCourseSerializer})
    def delete(self, request, resource_id):
        resource = (
            Resource.objects.select_related("lesson__module__course").filter(pk=resource_id).first()
        )
        if resource is None or not selectors.is_trainer(
            request.user, resource.lesson.module.course
        ):
            raise errors.CourseNotFound()
        course = resource.lesson.module.course
        courses.delete_resource(resource, request.user)
        return _studio(course)


class StudioQuestionsView(AcademyView):
    @extend_schema(
        tags=["academy"], request=s.QuestionInputSerializer, responses=s.StudioCourseSerializer
    )
    def post(self, request, module_id):
        data = s.QuestionInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        module = _studio_module(request, module_id)
        courses.save_question(module, request.user, **data.validated_data)
        return _studio(module.course)


def _studio_question(request, question_id) -> Question:
    question = (
        Question.objects.select_related("module__course__pro__user").filter(pk=question_id).first()
    )
    if question is None or not selectors.is_trainer(request.user, question.module.course):
        raise errors.CourseNotFound()
    return question


class StudioQuestionView(AcademyView):
    @extend_schema(
        tags=["academy"], request=s.QuestionInputSerializer, responses=s.StudioCourseSerializer
    )
    def patch(self, request, question_id):
        data = s.QuestionInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        question = _studio_question(request, question_id)
        courses.save_question(
            question.module, request.user, question_id=question.pk, **data.validated_data
        )
        return _studio(question.module.course)

    @extend_schema(tags=["academy"], request=None, responses={200: s.StudioCourseSerializer})
    def delete(self, request, question_id):
        question = _studio_question(request, question_id)
        course = question.module.course
        courses.delete_question(question, request.user)
        return _studio(course)


class StudioLivesView(AcademyView):
    @extend_schema(tags=["academy"], request=s.LiveInputSerializer, responses=s.LiveSerializer)
    def post(self, request):
        data = s.LiveInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = dict(data.validated_data)
        live = lives.plan_live(
            request.user,
            platform=values.pop("platform", False),
            country=values.pop("country", ""),
            course_id=values.pop("course_id", None),
            **values,
        )
        return Response(s.live_payload(lives.get_live(live.pk), False), status=201)


class StudioLiveCancelView(AcademyView):
    @extend_schema(tags=["academy"], request=None, responses=s.LiveSerializer)
    def post(self, request, live_id):
        live = lives.cancel_live(lives.get_live(live_id), request.user)
        return Response(s.live_payload(lives.get_live(live.pk), False))
