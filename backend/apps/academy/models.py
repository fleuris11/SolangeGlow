"""Academy (module 7): video courses cut into short lessons, quizzes, certificates, the
monthly pass and training lives. A course belongs to a pro or to the platform (no pro)."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


def _media_field(verbose_name, **extra):
    return models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=verbose_name,
        **extra,
    )


class Level(models.TextChoices):
    BEGINNER = "beginner", _("Beginner")
    INTERMEDIATE = "intermediate", _("Intermediate")
    EXPERT = "expert", _("Expert")


class CourseLanguage(models.TextChoices):
    FR = "fr", _("French")
    EN = "en", _("English")
    SK = "sk", _("Slovak")


class Course(BaseModel):
    class Pricing(models.TextChoices):
        FREE = "free", _("Free")
        PAID = "paid", _("Paid once")
        PASS = "pass", _("Included in the pass")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        IN_REVIEW = "in_review", _("Waiting for review")
        PUBLISHED = "published", _("Published")
        REJECTED = "rejected", _("Sent back")
        ARCHIVED = "archived", _("Archived")

    slug = models.SlugField(_("short link"), max_length=80, unique=True)
    pro = models.ForeignKey(
        "pros.ProProfile",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="courses",
        verbose_name=_("trainer"),
        help_text=_("Empty: a course of the platform."),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="authored_courses",
        verbose_name=_("written by"),
    )
    country = models.ForeignKey(
        "core.Country", on_delete=models.PROTECT, related_name="+", verbose_name=_("country")
    )
    title = models.CharField(_("title"), max_length=120)
    summary = models.CharField(_("in one sentence"), max_length=200, blank=True)
    description = models.TextField(_("description"), max_length=4000, blank=True)
    cover = _media_field(_("cover picture"))
    trade = models.ForeignKey(
        "pros.Trade",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
        verbose_name=_("trade"),
    )
    level = models.CharField(
        _("level"), max_length=12, choices=Level.choices, default=Level.BEGINNER
    )
    language = models.CharField(
        _("language"), max_length=2, choices=CourseLanguage.choices, default=CourseLanguage.FR
    )
    pricing = models.CharField(
        _("price"), max_length=8, choices=Pricing.choices, default=Pricing.FREE
    )
    price_minor = models.BigIntegerField(_("price (smallest unit)"), default=0)
    currency = models.CharField(_("currency"), max_length=3)
    status = models.CharField(
        _("status"), max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    review_note = models.TextField(_("note of the review"), blank=True)
    needs_recheck = models.BooleanField(
        _("changed since the review"),
        default=False,
        help_text=_("The trainer changed a published course: to look at again."),
    )
    submitted_at = models.DateTimeField(_("sent for review at"), null=True, blank=True)
    published_at = models.DateTimeField(_("published at"), null=True, blank=True)
    counts_for_badge = models.BooleanField(
        _("counts for the badge"),
        default=False,
        help_text=_("Finishing it gives the « Trained on Solange Glow » badge to a pro."),
    )
    duration_seconds = models.PositiveIntegerField(_("length (s)"), default=0, editable=False)
    students_count = models.PositiveIntegerField(_("students"), default=0, editable=False)

    class Meta:
        verbose_name = _("course")
        verbose_name_plural = _("courses")
        ordering = ["-published_at", "-created_at"]
        indexes = [models.Index(fields=["status", "country"], name="academy_course_listing")]
        permissions = [("review_course", _("Can publish or send back the courses of the pros"))]

    def __str__(self):
        return self.title

    @property
    def is_platform(self) -> bool:
        return self.pro_id is None

    @property
    def is_published(self) -> bool:
        return self.status == self.Status.PUBLISHED


class CourseReview(Course):
    """The queue of the team: courses of the pros waiting for review, or changed since."""

    class Meta:
        proxy = True
        verbose_name = _("course to review")
        verbose_name_plural = _("courses to review")


class Module(BaseModel):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="modules", verbose_name=_("course")
    )
    title = models.CharField(_("title"), max_length=120)
    position = models.PositiveSmallIntegerField(_("position"), default=0)

    class Meta:
        verbose_name = _("module")
        verbose_name_plural = _("modules")
        ordering = ["position", "created_at"]

    def __str__(self):
        return self.title


class Lesson(BaseModel):
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE, related_name="lessons", verbose_name=_("module")
    )
    title = models.CharField(_("title"), max_length=120)
    description = models.TextField(_("description"), max_length=2000, blank=True)
    video = _media_field(_("video"))
    duration_seconds = models.PositiveIntegerField(_("length (s)"), default=0)
    is_preview = models.BooleanField(
        _("free preview"), default=False, help_text=_("Everybody can watch it.")
    )
    position = models.PositiveSmallIntegerField(_("position"), default=0)

    class Meta:
        verbose_name = _("lesson")
        verbose_name_plural = _("lessons")
        ordering = ["position", "created_at"]

    def __str__(self):
        return self.title


class Resource(BaseModel):
    """A PDF given with a lesson (a sheet, a list of products)."""

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="resources", verbose_name=_("lesson")
    )
    title = models.CharField(_("title"), max_length=120)
    file = _media_field(_("PDF file"))
    position = models.PositiveSmallIntegerField(_("position"), default=0)

    class Meta:
        verbose_name = _("resource")
        verbose_name_plural = _("resources")
        ordering = ["position", "created_at"]


class Question(BaseModel):
    """A question of the quiz at the end of a module: one right answer among 2 to 4."""

    module = models.ForeignKey(
        Module, on_delete=models.CASCADE, related_name="questions", verbose_name=_("module")
    )
    text = models.CharField(_("question"), max_length=300)
    choices = models.JSONField(_("answers"), default=list)
    correct = models.PositiveSmallIntegerField(_("right answer (0 = the first)"), default=0)
    position = models.PositiveSmallIntegerField(_("position"), default=0)

    class Meta:
        verbose_name = _("quiz question")
        verbose_name_plural = _("quiz questions")
        ordering = ["position", "created_at"]


class Enrollment(BaseModel):
    """A student in a course: free, bought once or through the pass."""

    class Access(models.TextChoices):
        FREE = "free", _("Free")
        PURCHASE = "purchase", _("Bought")
        PASS = "pass", _("With the pass")
        TRAINER = "trainer", _("Trainer")
        POINTS = "points", _("With Glow Points")

    class Status(models.TextChoices):
        WAITING = "waiting", _("Waiting for the payment")
        ACTIVE = "active", _("Following")
        REFUNDED = "refunded", _("Refunded")

    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="enrollments", verbose_name=_("course")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name=_("student"),
    )
    access = models.CharField(_("access"), max_length=8, choices=Access.choices)
    status = models.CharField(
        _("status"), max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True
    )
    payment = models.ForeignKey(
        "payments.Payment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("payment"),
    )
    # The right to change her mind (14 days), given up when she opens the first lesson.
    waiver_at = models.DateTimeField(_("waiver ticked at"), null=True, blank=True)
    waiver_text = models.TextField(_("waiver wording"), blank=True)
    waiver_ip_hash = models.CharField(_("address (hashed)"), max_length=64, blank=True)
    started_at = models.DateTimeField(_("first lesson opened at"), null=True, blank=True)
    completed_at = models.DateTimeField(_("finished at"), null=True, blank=True)
    progress_percent = models.PositiveSmallIntegerField(_("progress (%)"), default=0)
    last_lesson = models.ForeignKey(
        Lesson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("last lesson"),
    )

    class Meta:
        verbose_name = _("student of a course")
        verbose_name_plural = _("students of the courses")
        constraints = [
            models.UniqueConstraint(fields=["course", "user"], name="academy_one_enrollment")
        ]

    def __str__(self):
        return f"{self.user} — {self.course}"


class LessonProgress(BaseModel):
    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, related_name="progress", verbose_name=_("student")
    )
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="+", verbose_name=_("lesson")
    )
    position_seconds = models.PositiveIntegerField(_("stopped at (s)"), default=0)
    completed_at = models.DateTimeField(_("watched at"), null=True, blank=True)

    class Meta:
        verbose_name = _("progress in a lesson")
        verbose_name_plural = _("progress in the lessons")
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "lesson"], name="academy_one_progress_per_lesson"
            )
        ]


class QuizAttempt(BaseModel):
    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, related_name="attempts", verbose_name=_("student")
    )
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE, related_name="+", verbose_name=_("module")
    )
    answers = models.JSONField(_("answers"), default=list)
    score_percent = models.PositiveSmallIntegerField(_("score (%)"), default=0)
    passed = models.BooleanField(_("passed"), default=False)

    class Meta:
        verbose_name = _("quiz attempt")
        verbose_name_plural = _("quiz attempts")
        ordering = ["-created_at"]


class Certificate(BaseModel):
    """Proof of a finished course; anybody can check it with its code (QR code)."""

    enrollment = models.OneToOneField(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="certificate",
        verbose_name=_("student"),
    )
    code = models.CharField(_("code"), max_length=16, unique=True)
    holder_name = models.CharField(_("name of the student"), max_length=120)
    course_title = models.CharField(_("course"), max_length=120)
    trainer_name = models.CharField(_("trainer"), max_length=120)
    issued_at = models.DateTimeField(_("issued at"))
    revoked_at = models.DateTimeField(_("cancelled at"), null=True, blank=True)
    revoked_reason = models.CharField(_("why it was cancelled"), max_length=200, blank=True)

    class Meta:
        verbose_name = _("certificate")
        verbose_name_plural = _("certificates")
        ordering = ["-issued_at"]

    def __str__(self):
        return self.code

    @property
    def is_valid(self) -> bool:
        return self.revoked_at is None


class AcademyPass(BaseModel):
    """The monthly pass: every course marked « included in the pass ». Paid month by month,
    never taken automatically."""

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        ENDED = "ended", _("Ended")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="academy_pass",
        verbose_name=_("student"),
    )
    country = models.ForeignKey(
        "core.Country", on_delete=models.PROTECT, related_name="+", verbose_name=_("country")
    )
    status = models.CharField(
        _("status"), max_length=8, choices=Status.choices, default=Status.ENDED, db_index=True
    )
    current_period_end = models.DateTimeField(_("paid until"), null=True, blank=True)
    cancel_at_period_end = models.BooleanField(_("stops at the end of the month"), default=False)
    renewal_payment = models.ForeignKey(
        "payments.Payment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("payment to make"),
    )
    renewal_noticed_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        verbose_name = _("academy pass")
        verbose_name_plural = _("academy passes")

    def __str__(self):
        return str(self.user)


class PassPeriod(BaseModel):
    academy_pass = models.ForeignKey(
        AcademyPass, on_delete=models.CASCADE, related_name="periods", verbose_name=_("pass")
    )
    starts_at = models.DateTimeField(_("from"))
    ends_at = models.DateTimeField(_("until"))
    payment = models.OneToOneField(
        "payments.Payment",
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=_("payment"),
    )

    class Meta:
        verbose_name = _("paid month of a pass")
        verbose_name_plural = _("paid months of the passes")
        ordering = ["-starts_at"]


class LiveSession(BaseModel):
    """A training live: planned, students register; the broadcast happens in the live room
    (apps.live, ADR-013)."""

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", _("Planned")
        LIVE = "live", _("On air")
        ENDED = "ended", _("Over")
        CANCELLED = "cancelled", _("Cancelled")

    pro = models.ForeignKey(
        "pros.ProProfile",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="lives",
        verbose_name=_("trainer"),
        help_text=_("Empty: a live of the platform."),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=_("planned by"),
    )
    country = models.ForeignKey(
        "core.Country", on_delete=models.PROTECT, related_name="+", verbose_name=_("country")
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lives",
        verbose_name=_("course"),
    )
    title = models.CharField(_("title"), max_length=120)
    description = models.TextField(_("description"), max_length=2000, blank=True)
    language = models.CharField(
        _("language"), max_length=2, choices=CourseLanguage.choices, default=CourseLanguage.FR
    )
    starts_at = models.DateTimeField(_("starts at"), db_index=True)
    duration_minutes = models.PositiveSmallIntegerField(_("length (min)"), default=60)
    capacity = models.PositiveIntegerField(_("places"), default=100)
    status = models.CharField(
        _("status"), max_length=10, choices=Status.choices, default=Status.SCHEDULED
    )
    registered_count = models.PositiveIntegerField(_("registered"), default=0, editable=False)

    class Meta:
        verbose_name = _("training live")
        verbose_name_plural = _("training lives")
        ordering = ["starts_at"]

    def __str__(self):
        return self.title


class LiveRegistration(BaseModel):
    live = models.ForeignKey(
        LiveSession,
        on_delete=models.CASCADE,
        related_name="registrations",
        verbose_name=_("live"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="live_registrations",
        verbose_name=_("student"),
    )
    reminded_day_at = models.DateTimeField(null=True, blank=True, editable=False)
    reminded_soon_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        verbose_name = _("registration to a live")
        verbose_name_plural = _("registrations to the lives")
        constraints = [
            models.UniqueConstraint(fields=["live", "user"], name="academy_one_registration")
        ]
