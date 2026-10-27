"""Back-office of the academy: the platform's courses, the review of the pros' courses,
students, certificates, passes and lives. Contents are written in the app (guided
creation screen); here the team reviews, publishes, sends back and sets the options."""

from __future__ import annotations

from django import forms
from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from unfold.admin import TabularInline
from unfold.decorators import action, display

from apps.core.audit.admin import AuditedModelAdmin
from apps.core.errors import DomainError
from apps.core.money import Money

from .models import (
    AcademyPass,
    Certificate,
    Course,
    CourseReview,
    Enrollment,
    Lesson,
    LiveSession,
    Module,
    PassPeriod,
    Question,
)
from .services import courses as course_services
from .services import progress

STATUS_LABELS = {
    "draft": "info",
    "in_review": "warning",
    "published": "success",
    "rejected": "danger",
    "archived": "info",
}


def money(value, currency) -> str:
    return Money(int(value or 0), currency).format("fr")


class ModuleInline(TabularInline):
    model = Module
    fields = ["position", "title"]
    readonly_fields = ["position", "title"]
    extra = 0
    tab = True
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


class LessonInline(TabularInline):
    model = Lesson
    fields = ["position", "title", "duration_seconds", "is_preview", "video"]
    readonly_fields = ["position", "title", "duration_seconds", "video"]
    extra = 0
    tab = True

    def has_add_permission(self, request, obj=None):
        return False


class QuestionInline(TabularInline):
    model = Question
    fields = ["position", "text", "choices", "correct"]
    readonly_fields = ["position"]
    extra = 0
    tab = True


class SendBackForm(forms.Form):
    note = forms.CharField(
        label=_("What the trainer should change"), max_length=2000, widget=forms.Textarea
    )


class CourseAdminBase(AuditedModelAdmin):
    list_display = [
        "title",
        "trainer",
        "country",
        "pricing",
        "price",
        "status_badge",
        "needs_recheck",
        "counts_for_badge",
        "students_count",
        "published_at",
    ]
    list_filter = ["status", "pricing", "needs_recheck", "counts_for_badge", "country", "level"]
    search_fields = ["title", "summary", "pro__business_name", "slug"]
    readonly_fields = [
        "slug",
        "pro",
        "author",
        "country",
        "currency",
        "status",
        "review_note",
        "submitted_at",
        "published_at",
        "duration_seconds",
        "students_count",
        "needs_recheck",
    ]
    fields = [
        "title",
        "slug",
        "pro",
        "author",
        "country",
        "summary",
        "description",
        "trade",
        "level",
        "language",
        "pricing",
        "price_minor",
        "currency",
        "counts_for_badge",
        "status",
        "needs_recheck",
        "review_note",
        "submitted_at",
        "published_at",
        "duration_seconds",
        "students_count",
    ]
    inlines = [ModuleInline]
    actions_detail = ["publish_detail", "send_back_detail"]

    def has_add_permission(self, request):
        return False  # written in the app, guided screen (« Academy » of the team)

    def has_review_course_permission(self, request, object_id=None):
        return request.user.has_perm("academy.review_course")

    @display(description=_("trainer"))
    def trainer(self, course):
        return course.pro.display_name if course.pro_id else "Solange Glow"

    @display(description=_("price"))
    def price(self, course):
        if course.pricing != Course.Pricing.PAID:
            return course.get_pricing_display()
        return money(course.price_minor, course.currency)

    @display(description=_("status"), ordering="status", label=STATUS_LABELS)
    def status_badge(self, course):
        return course.status, course.get_status_display()

    def _back(self, object_id):
        return redirect(
            reverse(f"admin:academy_{self.model._meta.model_name}_change", args=[object_id])
        )

    @action(
        description=_("Publish"),
        url_path="publish",
        icon="check_circle",
        permissions=["review_course"],
    )
    def publish_detail(self, request, object_id):
        course = get_object_or_404(Course, pk=object_id)
        try:
            course_services.approve(course, actor=request.user)
        except DomainError as exc:
            self.message_user(request, exc.text(), messages.ERROR)
        else:
            self.message_user(request, _("Published; the trainer is told."), messages.SUCCESS)
        return self._back(object_id)

    @action(
        description=_("Send back with a note"),
        url_path="send-back",
        icon="undo",
        permissions=["review_course"],
    )
    def send_back_detail(self, request, object_id):
        course = get_object_or_404(Course, pk=object_id)
        form = SendBackForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            try:
                course_services.reject(course, request.user, note=form.cleaned_data["note"])
            except DomainError as exc:
                self.message_user(request, exc.text(), messages.ERROR)
            else:
                self.message_user(request, _("Sent back; the trainer is told."), messages.SUCCESS)
            return self._back(object_id)
        context = {
            **self.admin_site.each_context(request),
            "title": _("Send back « %(title)s »") % {"title": course.title},
            "opts": self.model._meta,
            "form": form,
            "course": course,
            "back_url": reverse(
                f"admin:academy_{self.model._meta.model_name}_change", args=[object_id]
            ),
        }
        return TemplateResponse(request, "admin/academy/send_back.html", context)


@admin.register(Course)
class CourseAdmin(CourseAdminBase):
    pass


@admin.register(CourseReview)
class CourseReviewAdmin(CourseAdminBase):
    """Courses of the pros waiting for review, or changed after it."""

    list_filter = ["status", "country", "pricing"]

    def get_queryset(self, request):
        from django.db.models import Q

        return (
            super()
            .get_queryset(request)
            .filter(pro__isnull=False)
            .filter(Q(status=Course.Status.IN_REVIEW) | Q(needs_recheck=True))
            .order_by("submitted_at")
        )


@admin.register(Module)
class ModuleAdmin(AuditedModelAdmin):
    list_display = ["title", "course", "position"]
    search_fields = ["title", "course__title"]
    readonly_fields = ["course", "position"]
    fields = ["course", "title", "position"]
    inlines = [LessonInline, QuestionInline]

    def has_add_permission(self, request):
        return False

    def has_module_permission(self, request):
        return False  # reached from a course


@admin.register(Enrollment)
class EnrollmentAdmin(AuditedModelAdmin):
    list_display = [
        "user",
        "course",
        "access",
        "status",
        "progress_percent",
        "started_at",
        "completed_at",
        "created_at",
    ]
    list_filter = ["access", "status", "course__country"]
    search_fields = ["course__title", "user__first_name"]
    readonly_fields = [
        "course",
        "user",
        "access",
        "status",
        "payment",
        "waiver_at",
        "waiver_text",
        "started_at",
        "completed_at",
        "progress_percent",
        "last_lesson",
    ]
    fields = readonly_fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class RevokeForm(forms.Form):
    reason = forms.CharField(label=_("Why it is cancelled"), max_length=200)


@admin.register(Certificate)
class CertificateAdmin(AuditedModelAdmin):
    list_display = ["code", "holder_name", "course_title", "issued_at", "valid"]
    list_filter = ["revoked_at"]
    search_fields = ["code", "holder_name", "course_title"]
    readonly_fields = [
        "code",
        "enrollment",
        "holder_name",
        "course_title",
        "trainer_name",
        "issued_at",
        "revoked_at",
        "revoked_reason",
    ]
    fields = readonly_fields
    actions_detail = ["revoke_detail"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @display(description=_("valid"), boolean=True)
    def valid(self, certificate):
        return certificate.is_valid

    @action(description=_("Cancel the certificate"), url_path="revoke", icon="block")
    def revoke_detail(self, request, object_id):
        certificate = get_object_or_404(Certificate, pk=object_id)
        form = RevokeForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            progress.revoke(certificate, request.user, reason=form.cleaned_data["reason"])
            self.message_user(request, _("The certificate is cancelled."), messages.SUCCESS)
            return redirect(reverse("admin:academy_certificate_change", args=[object_id]))
        context = {
            **self.admin_site.each_context(request),
            "title": _("Cancel the certificate %(code)s") % {"code": certificate.code},
            "opts": self.model._meta,
            "form": form,
            "back_url": reverse("admin:academy_certificate_change", args=[object_id]),
        }
        return TemplateResponse(request, "admin/academy/revoke.html", context)


class PassPeriodInline(TabularInline):
    model = PassPeriod
    fields = ["starts_at", "ends_at", "payment"]
    readonly_fields = fields
    extra = 0
    tab = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(AcademyPass)
class AcademyPassAdmin(AuditedModelAdmin):
    list_display = ["user", "country", "status", "current_period_end", "cancel_at_period_end"]
    list_filter = ["status", "country"]
    search_fields = ["user__first_name"]
    readonly_fields = [
        "user",
        "country",
        "status",
        "current_period_end",
        "cancel_at_period_end",
        "renewal_payment",
    ]
    fields = readonly_fields
    inlines = [PassPeriodInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LiveSession)
class LiveSessionAdmin(AuditedModelAdmin):
    list_display = ["title", "trainer", "starts_at", "status", "registered_count", "capacity"]
    list_filter = ["status", "country", "language"]
    search_fields = ["title", "pro__business_name"]
    readonly_fields = ["pro", "author", "country", "course", "registered_count"]
    fields = [
        "title",
        "pro",
        "author",
        "country",
        "course",
        "description",
        "language",
        "starts_at",
        "duration_minutes",
        "capacity",
        "status",
        "registered_count",
    ]

    def has_add_permission(self, request):
        return False

    @display(description=_("trainer"))
    def trainer(self, live):
        return live.pro.display_name if live.pro_id else "Solange Glow"
