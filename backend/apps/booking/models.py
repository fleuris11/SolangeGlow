"""Bookings (module 8): the people of an agenda, their hours and time off, resources,
appointments made of timed steps, waiting lists, client files and the extras (last-minute
offers, group bookings, product advice).

Every pro has at least one staff member: herself (`is_owner`). The availability engine
(`availability.py`) works on staff members only, for a freelancer as for a salon.
"""

import secrets

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Func, Q
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from apps.core.models import BaseModel


def _token() -> str:
    return secrets.token_urlsafe(24)


class Weekday(models.IntegerChoices):
    MONDAY = 0, _("Monday")
    TUESDAY = 1, _("Tuesday")
    WEDNESDAY = 2, _("Wednesday")
    THURSDAY = 3, _("Thursday")
    FRIDAY = 4, _("Friday")
    SATURDAY = 5, _("Saturday")
    SUNDAY = 6, _("Sunday")


class BookingSettings(BaseModel):
    """How a pro takes bookings. Empty numbers take the platform settings."""

    pro = models.OneToOneField(
        "pros.ProProfile",
        on_delete=models.CASCADE,
        related_name="booking_settings",
        verbose_name=_("pro"),
    )
    auto_confirm = models.BooleanField(
        _("confirm by itself"), default=True, help_text=_("Off: you accept each request.")
    )
    slot_step_minutes = models.PositiveSmallIntegerField(
        _("slots every (min)"),
        default=15,
        validators=[MinValueValidator(5), MaxValueValidator(60)],
    )
    min_notice_minutes = models.PositiveIntegerField(
        _("minimum notice (min)"), null=True, blank=True
    )
    horizon_days = models.PositiveSmallIntegerField(
        _("bookable up to (days)"), null=True, blank=True
    )
    free_cancel_hours = models.PositiveSmallIntegerField(
        _("free cancellation until (hours before)"), null=True, blank=True
    )
    late_tolerance_minutes = models.PositiveSmallIntegerField(
        _("lateness accepted (min)"), null=True, blank=True
    )
    accepts_guests = models.BooleanField(_("guests can book"), default=True)
    ical_token = models.CharField(max_length=64, default=_token, editable=False, unique=True)

    class Meta:
        verbose_name = _("booking settings")
        verbose_name_plural = _("booking settings")

    def __str__(self):
        return str(self.pro)


class StaffMember(BaseModel):
    """A person of the agenda: the pro herself or a collaborator of her salon."""

    pro = models.ForeignKey(
        "pros.ProProfile", on_delete=models.CASCADE, related_name="staff", verbose_name=_("pro")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_memberships",
        verbose_name=_("account"),
    )
    name = models.CharField(_("name"), max_length=80)
    color = models.CharField(
        _("agenda colour"),
        max_length=7,
        default="#C8102E",
        validators=[RegexValidator(r"^#[0-9A-Fa-f]{6}$")],
    )
    is_owner = models.BooleanField(_("the pro herself"), default=False)
    phone = PhoneNumberField(_("phone (invitation)"), blank=True)
    invited_at = models.DateTimeField(_("invited at"), null=True, blank=True)
    services = models.ManyToManyField(
        "pros.Service",
        blank=True,
        related_name="staff",
        verbose_name=_("services allowed"),
        help_text=_("Empty: every service."),
    )
    daily_limit = models.PositiveSmallIntegerField(
        _("appointments per day at most"), null=True, blank=True
    )
    own_hours = models.BooleanField(
        _("own hours"), default=False, help_text=_("Off: the opening hours of the salon.")
    )
    position = models.PositiveSmallIntegerField(_("position"), default=0)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("staff member")
        verbose_name_plural = _("staff members")
        ordering = ["pro", "-is_owner", "position", "name"]

    def __str__(self):
        return self.name


class StaffPeriod(BaseModel):
    """Own working hours of a staff member (used when `own_hours` is on)."""

    staff = models.ForeignKey(
        StaffMember, on_delete=models.CASCADE, related_name="periods", verbose_name=_("person")
    )
    weekday = models.PositiveSmallIntegerField(_("day"), choices=Weekday.choices)
    starts_at = models.TimeField(_("from"))
    ends_at = models.TimeField(_("to"))

    class Meta:
        verbose_name = _("working hours")
        verbose_name_plural = _("working hours")
        ordering = ["weekday", "starts_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=models.F("starts_at")), name="booking_period_order"
            )
        ]

    def __str__(self):
        return f"{self.staff} {self.get_weekday_display()} {self.starts_at}-{self.ends_at}"


class StaffBreak(BaseModel):
    """A break that comes back every week (lunch…)."""

    staff = models.ForeignKey(
        StaffMember, on_delete=models.CASCADE, related_name="breaks", verbose_name=_("person")
    )
    weekday = models.PositiveSmallIntegerField(_("day"), choices=Weekday.choices)
    starts_at = models.TimeField(_("from"))
    ends_at = models.TimeField(_("to"))

    class Meta:
        verbose_name = _("break")
        verbose_name_plural = _("breaks")
        ordering = ["weekday", "starts_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=models.F("starts_at")), name="booking_break_order"
            )
        ]

    def __str__(self):
        return f"{self.staff} {self.get_weekday_display()} {self.starts_at}-{self.ends_at}"


class TimeOff(BaseModel):
    """An absence, holidays or a blocked range; for one person, or everyone when empty."""

    class Kind(models.TextChoices):
        ABSENCE = "absence", _("Absence")
        LEAVE = "leave", _("Holidays")
        BLOCK = "block", _("Blocked range")

    pro = models.ForeignKey(
        "pros.ProProfile", on_delete=models.CASCADE, related_name="time_off", verbose_name=_("pro")
    )
    staff = models.ForeignKey(
        StaffMember,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="time_off",
        verbose_name=_("person"),
        help_text=_("Empty: the whole salon."),
    )
    kind = models.CharField(_("type"), max_length=8, choices=Kind.choices, default=Kind.ABSENCE)
    starts_at = models.DateTimeField(_("from"))
    ends_at = models.DateTimeField(_("to"))
    note = models.CharField(_("note"), max_length=120, blank=True)

    class Meta:
        verbose_name = _("time off")
        verbose_name_plural = _("time off")
        ordering = ["starts_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=models.F("starts_at")), name="booking_timeoff_order"
            )
        ]

    def __str__(self):
        return f"{self.get_kind_display()} {self.starts_at:%Y-%m-%d %H:%M}"


class Resource(BaseModel):
    """Something a step needs (a chair, a room, a basin), in a given quantity."""

    pro = models.ForeignKey(
        "pros.ProProfile", on_delete=models.CASCADE, related_name="resources", verbose_name=_("pro")
    )
    name = models.CharField(_("name"), max_length=60)
    quantity = models.PositiveSmallIntegerField(
        _("how many"), default=1, validators=[MinValueValidator(1)]
    )
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("resource")
        verbose_name_plural = _("resources")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.quantity})"


class StepResource(BaseModel):
    """The resource a step of a service needs (held for the whole step, waiting included)."""

    step = models.OneToOneField(
        "pros.ServiceStep",
        on_delete=models.CASCADE,
        related_name="resource_need",
        verbose_name=_("step"),
    )
    resource = models.ForeignKey(
        Resource, on_delete=models.CASCADE, related_name="needs", verbose_name=_("resource")
    )

    class Meta:
        verbose_name = _("resource of a step")
        verbose_name_plural = _("resources of the steps")

    def __str__(self):
        return f"{self.step} → {self.resource}"


# --- Appointments --------------------------------------------------------------------------------


class GroupBooking(BaseModel):
    """Several people booked together (a bride and her bridesmaids), each pays her share."""

    class Status(models.TextChoices):
        COLLECTING = "collecting", _("Waiting for the shares")
        CONFIRMED = "confirmed", _("Confirmed")
        CANCELLED = "cancelled", _("Cancelled")

    pro = models.ForeignKey(
        "pros.ProProfile", on_delete=models.CASCADE, related_name="groups", verbose_name=_("pro")
    )
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="booking_groups",
        verbose_name=_("organiser"),
    )
    title = models.CharField(_("name"), max_length=80, blank=True)
    status = models.CharField(
        _("status"), max_length=10, choices=Status.choices, default=Status.COLLECTING
    )
    pay_by = models.DateTimeField(_("shares to pay before"), null=True, blank=True)
    share_token = models.CharField(max_length=64, default=_token, editable=False, unique=True)

    class Meta:
        verbose_name = _("group booking")
        verbose_name_plural = _("group bookings")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or str(self.pk)


class Appointment(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", _("Waiting for the pro")
        AWAITING_DEPOSIT = "awaiting_deposit", _("Waiting for the deposit")
        CONFIRMED = "confirmed", _("Confirmed")
        PROPOSED = "proposed", _("Other time proposed")
        HELD = "held", _("Kept for the waiting list")
        DECLINED = "declined", _("Declined")
        CANCELLED = "cancelled", _("Cancelled")
        COMPLETED = "completed", _("Done")
        NO_SHOW = "no_show", _("Client did not come")
        EXPIRED = "expired", _("Expired")

    # The statuses that keep the time in the agenda.
    BLOCKING = (
        Status.PENDING,
        Status.AWAITING_DEPOSIT,
        Status.CONFIRMED,
        Status.PROPOSED,
        Status.HELD,
    )

    class Source(models.TextChoices):
        ONLINE = "online", _("Online")
        PHONE = "phone", _("By phone")
        WAITLIST = "waitlist", _("Waiting list")
        GROUP = "group", _("Group")
        LOOK = "look", _("« Book this look »")

    class CancelledBy(models.TextChoices):
        CLIENT = "client", _("The client")
        PRO = "pro", _("The pro")
        SYSTEM = "system", _("Automatically")

    reference = models.CharField(_("reference"), max_length=20, unique=True)
    pro = models.ForeignKey(
        "pros.ProProfile",
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name=_("pro"),
    )
    service = models.ForeignKey(
        "pros.Service",
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name=_("service"),
    )
    options = models.ManyToManyField(
        "pros.ServiceOption", blank=True, related_name="+", verbose_name=_("options")
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments",
        verbose_name=_("client"),
    )
    guest = models.ForeignKey(
        "accounts.GuestIdentity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments",
        verbose_name=_("guest"),
    )
    client_name = models.CharField(_("client name"), max_length=150)
    client_phone = models.CharField(_("client phone"), max_length=20, blank=True)
    starts_at = models.DateTimeField(_("starts at"), db_index=True)
    ends_at = models.DateTimeField(_("ends at"))
    status = models.CharField(
        _("status"), max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    source = models.CharField(
        _("made"), max_length=10, choices=Source.choices, default=Source.ONLINE
    )
    price_minor = models.BigIntegerField(_("price"), null=True, blank=True)
    currency = models.CharField(_("currency"), max_length=3)
    discount_percent = models.PositiveSmallIntegerField(_("last-minute discount (%)"), default=0)
    deposit_minor = models.BigIntegerField(_("deposit"), default=0)
    payment = models.OneToOneField(
        "payments.Payment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointment",
        verbose_name=_("deposit payment"),
    )
    note = models.CharField(_("note from the client"), max_length=500, blank=True)
    pro_message = models.CharField(_("message from the pro"), max_length=500, blank=True)
    proposed_from = models.DateTimeField(_("time asked first"), null=True, blank=True)
    answer_due_at = models.DateTimeField(_("answer before"), null=True, blank=True)
    group = models.ForeignKey(
        GroupBooking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments",
        verbose_name=_("group"),
    )
    post = models.ForeignKey(
        "social.Post",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("look"),
    )
    manage_token = models.CharField(max_length=64, default=_token, editable=False, unique=True)
    reminders_sent = models.JSONField(default=list, blank=True, editable=False)
    confirmed_at = models.DateTimeField(_("confirmed at"), null=True, blank=True)
    completed_at = models.DateTimeField(_("done at"), null=True, blank=True)
    cancelled_at = models.DateTimeField(_("cancelled at"), null=True, blank=True)
    cancelled_by = models.CharField(
        _("cancelled by"), max_length=8, choices=CancelledBy.choices, blank=True
    )

    class Meta:
        verbose_name = _("appointment")
        verbose_name_plural = _("appointments")
        ordering = ["starts_at"]
        indexes = [
            models.Index(fields=["pro", "starts_at"]),
            models.Index(fields=["client", "starts_at"]),
        ]

    def __str__(self):
        return f"{self.reference} {self.client_name}"

    @property
    def is_blocking(self) -> bool:
        return self.status in self.BLOCKING


class TsTzRange(Func):
    function = "TSTZRANGE"
    output_field = DateTimeRangeField()


class AppointmentStep(BaseModel):
    """A timed step of an appointment: who does it, with which resource."""

    appointment = models.ForeignKey(
        Appointment, on_delete=models.CASCADE, related_name="steps", verbose_name=_("appointment")
    )
    position = models.PositiveSmallIntegerField(_("position"))
    kind = models.CharField(_("type"), max_length=4)  # work / wait (pros.ServiceStep.Kind)
    label = models.CharField(_("label"), max_length=60, blank=True)
    starts_at = models.DateTimeField(_("from"))
    ends_at = models.DateTimeField(_("to"))
    staff = models.ForeignKey(
        StaffMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="steps",
        verbose_name=_("person"),
    )
    resource = models.ForeignKey(
        Resource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="steps",
        verbose_name=_("resource"),
    )
    # True while the appointment keeps its time and someone works on this step: the
    # database then refuses two such steps of the same person at the same time.
    blocking = models.BooleanField(default=True, editable=False)

    class Meta:
        verbose_name = _("step of an appointment")
        verbose_name_plural = _("steps of an appointment")
        ordering = ["starts_at", "position"]
        indexes = [models.Index(fields=["staff", "starts_at"])]
        constraints = [
            ExclusionConstraint(
                name="booking_no_double_booking",
                expressions=[
                    ("staff", RangeOperators.EQUAL),
                    (TsTzRange("starts_at", "ends_at"), RangeOperators.OVERLAPS),
                ],
                condition=Q(blocking=True, staff__isnull=False),
            )
        ]

    def __str__(self):
        return f"{self.appointment} #{self.position}"


class AppointmentPhoto(BaseModel):
    """A picture of the result, kept in the client file."""

    appointment = models.ForeignKey(
        Appointment, on_delete=models.CASCADE, related_name="photos", verbose_name=_("appointment")
    )
    media = models.ForeignKey(
        "core.MediaAsset", on_delete=models.CASCADE, related_name="+", verbose_name=_("photo")
    )

    class Meta:
        verbose_name = _("result photo")
        verbose_name_plural = _("result photos")
        ordering = ["created_at"]

    def __str__(self):
        return str(self.appointment)


class Recommendation(BaseModel):
    """After the appointment, the pro advises a product of her shop."""

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="recommendations",
        verbose_name=_("appointment"),
    )
    product = models.ForeignKey(
        "shop.Product", on_delete=models.CASCADE, related_name="+", verbose_name=_("product")
    )
    note = models.CharField(_("why"), max_length=300, blank=True)

    class Meta:
        verbose_name = _("product advice")
        verbose_name_plural = _("product advice")
        constraints = [
            models.UniqueConstraint(fields=["appointment", "product"], name="booking_advice_once")
        ]

    def __str__(self):
        return f"{self.appointment} → {self.product}"


# --- Waiting list, client files, last minute ------------------------------------------------------


class WaitlistEntry(BaseModel):
    class Status(models.TextChoices):
        WAITING = "waiting", _("Waiting")
        OFFERED = "offered", _("Place offered")
        BOOKED = "booked", _("Booked")
        EXPIRED = "expired", _("No answer")
        CANCELLED = "cancelled", _("Cancelled")

    pro = models.ForeignKey(
        "pros.ProProfile", on_delete=models.CASCADE, related_name="waitlist", verbose_name=_("pro")
    )
    service = models.ForeignKey(
        "pros.Service", on_delete=models.CASCADE, related_name="+", verbose_name=_("service")
    )
    staff = models.ForeignKey(
        StaffMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("person"),
    )
    day = models.DateField(_("day"))
    from_time = models.TimeField(_("from"), null=True, blank=True)
    to_time = models.TimeField(_("to"), null=True, blank=True)
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="waitlist_entries",
        verbose_name=_("client"),
    )
    guest = models.ForeignKey(
        "accounts.GuestIdentity",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="waitlist_entries",
        verbose_name=_("guest"),
    )
    status = models.CharField(
        _("status"), max_length=10, choices=Status.choices, default=Status.WAITING, db_index=True
    )
    offer = models.OneToOneField(
        Appointment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="waitlist_entry",
        verbose_name=_("place kept"),
    )
    offer_expires_at = models.DateTimeField(_("answer before"), null=True, blank=True)

    class Meta:
        verbose_name = _("waiting list entry")
        verbose_name_plural = _("waiting list")
        ordering = ["day", "created_at"]

    def __str__(self):
        return f"{self.service} {self.day}"


class ClientRecord(BaseModel):
    """What a pro keeps about one of her clients (private): notes, preferences."""

    pro = models.ForeignKey(
        "pros.ProProfile",
        on_delete=models.CASCADE,
        related_name="client_records",
        verbose_name=_("pro"),
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("client"),
    )
    phone = models.CharField(_("phone"), max_length=20, blank=True)
    name = models.CharField(_("name"), max_length=150)
    notes = models.TextField(_("private notes"), max_length=2000, blank=True)
    preferences = models.TextField(_("preferences"), max_length=1000, blank=True)
    email = models.EmailField(_("e-mail"), blank=True)
    birthday_day = models.PositiveSmallIntegerField(
        _("birthday (day)"),
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
    )
    birthday_month = models.PositiveSmallIntegerField(
        _("birthday (month)"),
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )

    class Meta:
        verbose_name = _("client file")
        verbose_name_plural = _("client files")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["pro", "client"],
                condition=Q(client__isnull=False),
                name="booking_file_user",
            ),
            models.UniqueConstraint(
                fields=["pro", "phone"],
                condition=Q(client__isnull=True) & ~Q(phone=""),
                name="booking_file_phone",
            ),
        ]

    def __str__(self):
        return self.name


class LastMinuteOffer(BaseModel):
    """A discount on the free slots of the next hours, pushed to clients nearby."""

    pro = models.OneToOneField(
        "pros.ProProfile",
        on_delete=models.CASCADE,
        related_name="last_minute",
        verbose_name=_("pro"),
    )
    percent_off = models.PositiveSmallIntegerField(
        _("discount (%)"), default=20, validators=[MinValueValidator(5), MaxValueValidator(70)]
    )
    window_hours = models.PositiveSmallIntegerField(
        _("for the slots of the next (hours)"),
        default=24,
        validators=[MinValueValidator(1), MaxValueValidator(72)],
    )
    is_active = models.BooleanField(_("active"), default=False)
    announced_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        verbose_name = _("last-minute offer")
        verbose_name_plural = _("last-minute offers")

    def __str__(self):
        return f"{self.pro} -{self.percent_off} %"


class LastMinuteAlert(BaseModel):
    """One last-minute alert a day at most for a client."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    pro = models.ForeignKey("pros.ProProfile", on_delete=models.CASCADE, related_name="+")
    sent_on = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "sent_on"], name="booking_one_alert_a_day")
        ]
