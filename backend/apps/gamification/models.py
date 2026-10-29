"""The playful side (module 10, ADR-015): Glow Points, streaks, daily quiz, weekly photo
challenge, « Help me choose » polls, the free Glow wheel, levels, monthly rankings,
referrals, the beauty routine and the calendar of celebrations.

Points live in an append-only ledger (``PointsEntry``): a gain or a spending is written
once, under a unique key, and never changed (a database trigger refuses it). The balance
is always computed from the entries.
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel
from apps.gifts.models import Occasion
from apps.social.models import Visibility


def _media(verbose_name, *, null=True):
    return models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL if null else models.PROTECT,
        null=null,
        blank=null,
        related_name="+",
        verbose_name=verbose_name,
    )


class Level(models.TextChoices):
    """Levels of the clients, reached with the points earned since the beginning."""

    GLOW = "glow", _("Glow")
    STAR = "star", _("Star")
    ICON = "icon", _("Icon")


LEVEL_ORDER = [Level.GLOW, Level.STAR, Level.ICON]


class Action(models.TextChoices):
    CHECKIN = "checkin", _("Daily visit")
    STREAK = "streak", _("Streak bonus")
    POST = "post", _("Post")
    REVIEW = "review", _("Review")
    BOOKING = "booking", _("Appointment")
    PURCHASE = "purchase", _("Purchase")
    REFERRAL = "referral", _("Friend invited")
    REFERRED = "referred", _("Welcome bonus")
    QUIZ = "quiz", _("Quiz")
    POLL = "poll", _("Help me choose")
    POLL_VOTE = "poll_vote", _("Vote")
    CHALLENGE_ENTRY = "challenge_entry", _("Photo challenge")
    CHALLENGE_VOTE = "challenge_vote", _("Challenge vote")
    CHALLENGE_WIN = "challenge_win", _("Challenge won")
    WHEEL = "wheel", _("Glow wheel")
    ROUTINE = "routine", _("Routine")
    REWARD = "reward", _("Reward")
    ADJUSTMENT = "adjustment", _("Adjustment by the team")


class GlowProfile(BaseModel):
    """What the games know about a person: streak, level, referral code, reminders."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="glow",
        verbose_name=_("person"),
    )
    streak = models.PositiveIntegerField(_("days in a row"), default=0)
    best_streak = models.PositiveIntegerField(_("best streak"), default=0)
    last_checkin_on = models.DateField(_("last visit"), null=True, blank=True)
    earned_total = models.PositiveIntegerField(_("points earned in total"), default=0)
    level = models.CharField(_("level"), max_length=8, choices=Level.choices, default=Level.GLOW)
    referral_code = models.CharField(_("referral code"), max_length=12, unique=True)
    routine_reminders = models.BooleanField(_("routine reminders"), default=False)
    morning_at = models.TimeField(_("morning reminder"), default="07:30")
    evening_at = models.TimeField(_("evening reminder"), default="21:00")
    morning_reminded_on = models.DateField(null=True, blank=True, editable=False)
    evening_reminded_on = models.DateField(null=True, blank=True, editable=False)
    celebration_reminders = models.BooleanField(_("celebration reminders"), default=True)

    class Meta:
        verbose_name = _("Glow profile")
        verbose_name_plural = _("Glow profiles")

    def __str__(self):
        return str(self.user)


class PointsEntry(BaseModel):
    """One gain (positive) or one spending (negative). Never changed, never deleted."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="points_entries",
        verbose_name=_("person"),
    )
    amount = models.IntegerField(_("points"))
    action = models.CharField(_("for"), max_length=16, choices=Action.choices, db_index=True)
    key = models.CharField(_("unique key"), max_length=120, unique=True)
    source_type = models.CharField(_("source"), max_length=30, blank=True)
    source_id = models.CharField(_("source id"), max_length=64, blank=True)
    # Day of the person (her time zone): daily caps are counted on it.
    day = models.DateField(_("day"), db_index=True)
    note = models.CharField(_("note"), max_length=200, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("by"),
    )

    class Meta:
        verbose_name = _("points entry")
        verbose_name_plural = _("points ledger")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "day", "action"], name="glow_points_user_day")]
        constraints = [
            models.CheckConstraint(condition=~models.Q(amount=0), name="glow_points_not_zero")
        ]

    def __str__(self):
        return f"{self.amount:+d} {self.action}"


# --- Rewards and vouchers -------------------------------------------------------------------


class Voucher(BaseModel):
    """A discount paid by the platform, only on what the platform sells itself (France
    Selection): a pro never pays for the points of her clients."""

    class Kind(models.TextChoices):
        AMOUNT_OFF = "amount_off", _("Discount on the France Selection")
        EXPRESS = "express", _("Express shipping for free")

    class Origin(models.TextChoices):
        REWARD = "reward", _("Points exchanged")
        WHEEL = "wheel", _("Glow wheel")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="glow_vouchers",
        verbose_name=_("person"),
    )
    kind = models.CharField(_("kind"), max_length=12, choices=Kind.choices)
    origin = models.CharField(_("origin"), max_length=8, choices=Origin.choices)
    code = models.CharField(_("code"), max_length=16, unique=True)
    label = models.CharField(_("label"), max_length=120)
    amount_off_minor = models.BigIntegerField(_("discount (FCFA)"), default=0)
    currency = models.CharField(_("currency"), max_length=3, default="XOF")
    expires_at = models.DateTimeField(_("valid until"))
    used_at = models.DateTimeField(_("used at"), null=True, blank=True)
    used_for_type = models.CharField(_("used for"), max_length=30, blank=True)
    used_for_id = models.UUIDField(_("used for (id)"), null=True, blank=True)

    class Meta:
        verbose_name = _("voucher")
        verbose_name_plural = _("vouchers")
        ordering = ["-created_at"]

    def __str__(self):
        return self.code


class Reward(BaseModel):
    """What points buy (catalogue edited in the admin)."""

    class Kind(models.TextChoices):
        AMOUNT_OFF = "amount_off", _("Discount on the France Selection")
        EXPRESS = "express", _("Express shipping for free (France Selection)")
        COURSE = "course", _("A course of the platform")

    title = models.CharField(_("title"), max_length=80)
    description = models.CharField(_("description"), max_length=200, blank=True)
    kind = models.CharField(_("kind"), max_length=12, choices=Kind.choices)
    cost_points = models.PositiveIntegerField(_("cost (points)"), validators=[MinValueValidator(1)])
    amount_off_minor = models.BigIntegerField(
        _("discount (FCFA)"), default=0, help_text=_("For a discount only.")
    )
    course = models.ForeignKey(
        "academy.Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        limit_choices_to={"pro__isnull": True},
        verbose_name=_("course"),
        help_text=_("A course of the platform (not of a pro)."),
    )
    min_level = models.CharField(
        _("from the level"), max_length=8, choices=Level.choices, default=Level.GLOW
    )
    countries = models.JSONField(
        _("countries"),
        default=list,
        blank=True,
        help_text=_('Country codes, e.g. ["BJ"]. Empty: everywhere.'),
    )
    stock = models.PositiveIntegerField(
        _("left"), null=True, blank=True, help_text=_("Empty: no limit.")
    )
    validity_days = models.PositiveSmallIntegerField(_("voucher valid (days)"), default=30)
    position = models.PositiveSmallIntegerField(_("position"), default=0)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("reward")
        verbose_name_plural = _("rewards")
        ordering = ["position", "cost_points"]

    def __str__(self):
        return self.title


# --- Daily quiz -----------------------------------------------------------------------------


class QuizDay(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        APPROVED = "approved", _("Approved")

    date = models.DateField(_("day"), unique=True)
    status = models.CharField(
        _("status"), max_length=8, choices=Status.choices, default=Status.DRAFT
    )
    generated_by = models.CharField(_("prepared by"), max_length=30, blank=True)
    approved_at = models.DateTimeField(_("approved at"), null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("approved by"),
    )

    class Meta:
        verbose_name = _("quiz of the day")
        verbose_name_plural = _("quizzes of the day")
        ordering = ["-date"]

    def __str__(self):
        return str(self.date)


class QuizQuestion(BaseModel):
    quiz = models.ForeignKey(
        QuizDay, on_delete=models.CASCADE, related_name="questions", verbose_name=_("quiz")
    )
    position = models.PositiveSmallIntegerField(_("position"), default=0)
    text = models.CharField(_("question"), max_length=200)
    choice_1 = models.CharField(_("answer 1"), max_length=80)
    choice_2 = models.CharField(_("answer 2"), max_length=80)
    choice_3 = models.CharField(_("answer 3"), max_length=80, blank=True)
    choice_4 = models.CharField(_("answer 4"), max_length=80, blank=True)
    answer = models.PositiveSmallIntegerField(
        _("right answer (1 to 4)"), validators=[MinValueValidator(1), MaxValueValidator(4)]
    )
    explanation = models.CharField(_("explanation"), max_length=300, blank=True)
    image = _media(_("picture"))
    audio = _media(_("audio"))

    class Meta:
        verbose_name = _("question")
        verbose_name_plural = _("questions")
        ordering = ["quiz", "position"]

    def __str__(self):
        return self.text

    def choices(self) -> list[str]:
        return [c for c in (self.choice_1, self.choice_2, self.choice_3, self.choice_4) if c]


class QuizAnswer(BaseModel):
    question = models.ForeignKey(
        QuizQuestion, on_delete=models.CASCADE, related_name="answers", verbose_name=_("question")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_answers",
        verbose_name=_("person"),
    )
    choice = models.PositiveSmallIntegerField(_("answer"))
    is_correct = models.BooleanField(_("right"))

    class Meta:
        verbose_name = _("quiz answer")
        verbose_name_plural = _("quiz answers")
        constraints = [models.UniqueConstraint(fields=["question", "user"], name="glow_one_answer")]


# --- « Help me choose » ---------------------------------------------------------------------


class Poll(BaseModel):
    """Two photos (two outfits, two hairstyles): the community votes until the end."""

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="polls",
        verbose_name=_("author"),
    )
    caption = models.CharField(_("question"), max_length=140)
    photo_a = _media(_("photo A"), null=False)
    photo_b = _media(_("photo B"), null=False)
    label_a = models.CharField(_("name of A"), max_length=40, blank=True)
    label_b = models.CharField(_("name of B"), max_length=40, blank=True)
    ends_at = models.DateTimeField(_("ends at"), db_index=True)
    votes_a = models.PositiveIntegerField(_("votes A"), default=0)
    votes_b = models.PositiveIntegerField(_("votes B"), default=0)
    city = models.CharField(_("city"), max_length=80, blank=True)
    visibility = models.CharField(
        _("visibility"), max_length=10, choices=Visibility.choices, default=Visibility.VISIBLE
    )
    result_sent_at = models.DateTimeField(_("result sent at"), null=True, blank=True)
    deleted_at = models.DateTimeField(_("deleted at"), null=True, blank=True)

    class Meta:
        verbose_name = _("« Help me choose »")
        verbose_name_plural = _("« Help me choose »")
        ordering = ["-created_at"]

    def __str__(self):
        return self.caption


class PollVote(BaseModel):
    class Choice(models.TextChoices):
        A = "a", "A"
        B = "b", "B"

    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    choice = models.CharField(max_length=1, choices=Choice.choices)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["poll", "user"], name="glow_one_poll_vote")]


# --- Weekly photo challenge -----------------------------------------------------------------


class Challenge(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        APPROVED = "approved", _("Approved")
        CLOSED = "closed", _("Closed")

    theme = models.CharField(_("theme"), max_length=80)
    description = models.CharField(_("description"), max_length=240, blank=True)
    starts_on = models.DateField(_("from (Monday)"), unique=True)
    ends_on = models.DateField(_("until (Sunday)"))
    status = models.CharField(
        _("status"), max_length=8, choices=Status.choices, default=Status.DRAFT
    )
    generated_by = models.CharField(_("prepared by"), max_length=30, blank=True)
    winner = models.ForeignKey(
        "ChallengeEntry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("winner"),
    )
    closed_at = models.DateTimeField(_("closed at"), null=True, blank=True)

    class Meta:
        verbose_name = _("photo challenge")
        verbose_name_plural = _("photo challenges")
        ordering = ["-starts_on"]

    def __str__(self):
        return self.theme


class ChallengeEntry(BaseModel):
    challenge = models.ForeignKey(
        Challenge, on_delete=models.CASCADE, related_name="entries", verbose_name=_("challenge")
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="challenge_entries",
        verbose_name=_("author"),
    )
    photo = _media(_("photo"), null=False)
    caption = models.CharField(_("caption"), max_length=140, blank=True)
    votes = models.PositiveIntegerField(_("votes"), default=0)
    visibility = models.CharField(
        _("visibility"), max_length=10, choices=Visibility.choices, default=Visibility.VISIBLE
    )

    class Meta:
        verbose_name = _("challenge entry")
        verbose_name_plural = _("challenge entries")
        ordering = ["-votes", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["challenge", "author"], name="glow_one_entry")
        ]

    def __str__(self):
        return f"{self.challenge} — {self.author}"


class ChallengeVote(BaseModel):
    entry = models.ForeignKey(ChallengeEntry, on_delete=models.CASCADE, related_name="vote_rows")
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="+")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["entry", "user"], name="glow_one_challenge_vote")
        ]


# --- Glow wheel -----------------------------------------------------------------------------


class WheelPrize(BaseModel):
    """A slice of the wheel. Its chance = its weight / the weights of the prizes available."""

    class Kind(models.TextChoices):
        POINTS = "points", _("Points")
        AMOUNT_OFF = "amount_off", _("Discount on the France Selection")
        EXPRESS = "express", _("Express shipping for free")
        NOTHING = "nothing", _("Try again tomorrow")

    label = models.CharField(_("label"), max_length=40)
    kind = models.CharField(_("kind"), max_length=12, choices=Kind.choices)
    points = models.PositiveIntegerField(_("points"), default=0)
    amount_off_minor = models.BigIntegerField(_("discount (FCFA)"), default=0)
    weight = models.PositiveIntegerField(
        _("weight"), help_text=_("The higher, the more often. 0: never.")
    )
    daily_stock = models.PositiveIntegerField(
        _("per day"), null=True, blank=True, help_text=_("Empty: no limit.")
    )
    countries = models.JSONField(
        _("countries"), default=list, blank=True, help_text=_("Empty: everywhere.")
    )
    validity_days = models.PositiveSmallIntegerField(_("voucher valid (days)"), default=14)
    position = models.PositiveSmallIntegerField(_("position"), default=0)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("wheel prize")
        verbose_name_plural = _("Glow wheel")
        ordering = ["position", "label"]

    def __str__(self):
        return self.label


class WheelSpin(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wheel_spins",
        verbose_name=_("person"),
    )
    day = models.DateField(_("day"))
    prize = models.ForeignKey(
        WheelPrize, on_delete=models.SET_NULL, null=True, related_name="spins"
    )
    kind = models.CharField(_("kind"), max_length=12, choices=WheelPrize.Kind.choices)
    label = models.CharField(_("prize"), max_length=40)
    points = models.PositiveIntegerField(_("points"), default=0)
    voucher = models.ForeignKey(
        Voucher, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = _("spin")
        verbose_name_plural = _("spins")
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "day"], name="glow_one_spin")]


# --- Pros: monthly rankings -----------------------------------------------------------------


class Ranking(BaseModel):
    """Top pros of a month, per city and trade, computed on the verified reviews."""

    month = models.DateField(_("month"))
    city = models.CharField(_("city"), max_length=80)
    trade = models.ForeignKey(
        "pros.Trade", on_delete=models.CASCADE, related_name="+", verbose_name=_("trade")
    )
    pro = models.ForeignKey(
        "pros.ProProfile", on_delete=models.CASCADE, related_name="rankings", verbose_name=_("pro")
    )
    position = models.PositiveSmallIntegerField(_("position"))
    score = models.DecimalField(_("score"), max_digits=4, decimal_places=2)
    average = models.DecimalField(_("average"), max_digits=3, decimal_places=2)
    reviews = models.PositiveIntegerField(_("reviews of the month"))

    class Meta:
        verbose_name = _("ranking")
        verbose_name_plural = _("rankings")
        ordering = ["-month", "city", "trade", "position"]
        constraints = [
            models.UniqueConstraint(fields=["month", "city", "trade", "pro"], name="glow_one_rank")
        ]


# --- Referrals ------------------------------------------------------------------------------


class Referral(BaseModel):
    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referrals",
        verbose_name=_("godmother"),
    )
    referee = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referred_by",
        verbose_name=_("goddaughter"),
    )
    rewarded_at = models.DateTimeField(_("points given at"), null=True, blank=True)
    payment = models.ForeignKey(
        "payments.Payment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("first purchase"),
    )
    capped = models.BooleanField(_("over the monthly limit"), default=False)

    class Meta:
        verbose_name = _("referral")
        verbose_name_plural = _("referrals")
        ordering = ["-created_at"]


# --- My routine -----------------------------------------------------------------------------


class Moment(models.TextChoices):
    MORNING = "morning", _("Morning")
    EVENING = "evening", _("Evening")


class RoutineStep(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="routine_steps",
        verbose_name=_("person"),
    )
    moment = models.CharField(_("moment"), max_length=8, choices=Moment.choices)
    label = models.CharField(_("step"), max_length=60)
    position = models.PositiveSmallIntegerField(_("position"), default=0)

    class Meta:
        verbose_name = _("routine step")
        verbose_name_plural = _("routine steps")
        ordering = ["moment", "position"]

    def __str__(self):
        return self.label


class RoutineCheck(BaseModel):
    step = models.ForeignKey(RoutineStep, on_delete=models.CASCADE, related_name="checks")
    day = models.DateField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["step", "day"], name="glow_one_check")]


# --- Calendar of celebrations ---------------------------------------------------------------


class Celebration(BaseModel):
    """A big day (Mother's day, Tabaski, Christmas…): a reminder a few days before, with the
    pros and the products of the moment."""

    name = models.CharField(_("name"), max_length=80)
    message = models.CharField(_("reminder"), max_length=200, blank=True)
    date = models.DateField(
        _("date"), help_text=_("For a moving day (Tabaski, Easter…), write each year's date.")
    )
    yearly = models.BooleanField(_("same date every year"), default=False)
    countries = models.JSONField(
        _("countries"), default=list, blank=True, help_text=_("Empty: everywhere.")
    )
    remind_days = models.PositiveSmallIntegerField(_("reminder (days before)"), default=7)
    trade = models.ForeignKey(
        "pros.Trade",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("pros of the moment"),
    )
    search = models.CharField(
        _("products of the moment"), max_length=60, blank=True, help_text=_("Words searched.")
    )
    gift_occasion = models.CharField(
        _("gift occasion"), max_length=20, choices=Occasion.choices, blank=True
    )
    reminded_for = models.DateField(_("last reminder for"), null=True, blank=True, editable=False)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("celebration")
        verbose_name_plural = _("calendar of celebrations")
        ordering = ["date"]

    def __str__(self):
        return self.name
