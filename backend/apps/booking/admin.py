"""Appointments in the back office: the agenda of every salon (read only, an appointment can
be cancelled with a refund in one click), people, hours, resources, waiting lists, groups,
last-minute offers. Client files show no notes: they belong to the pro."""

from __future__ import annotations

from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import TabularInline
from unfold.decorators import action, display

from apps.core.audit.admin import AuditedModelAdmin
from apps.core.errors import DomainError
from apps.core.money import Money

from .models import (
    Appointment,
    AppointmentStep,
    BookingSettings,
    ClientRecord,
    GroupBooking,
    LastMinuteOffer,
    Resource,
    StaffBreak,
    StaffMember,
    StaffPeriod,
    TimeOff,
    WaitlistEntry,
)
from .services import appointments

STATUS_LABELS = {
    "pending": "warning",
    "awaiting_deposit": "warning",
    "confirmed": "success",
    "proposed": "info",
    "held": "info",
    "declined": "danger",
    "cancelled": "danger",
    "completed": "success",
    "no_show": "danger",
    "expired": "info",
}


def amount(value, currency) -> str:
    return Money(value or 0, currency).format("fr") if value is not None else "—"


class ReadOnlyMixin:
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class StepInline(ReadOnlyMixin, TabularInline):
    model = AppointmentStep
    fields = ["position", "kind", "label", "starts_at", "ends_at", "staff", "resource", "blocking"]
    readonly_fields = fields
    extra = 0
    tab = True

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Appointment)
class AppointmentAdmin(AuditedModelAdmin):
    """Read only: the pro manages her agenda; the team can cancel with a refund."""

    list_display = [
        "reference",
        "pro",
        "service",
        "client_name",
        "starts_at",
        "status_badge",
        "source",
        "deposit",
    ]
    list_filter = ["status", "source", "pro__country"]
    search_fields = ["reference", "client_name", "pro__business_name", "pro__slug"]
    date_hierarchy = "starts_at"
    inlines = [StepInline]
    exclude = ["client_phone", "manage_token", "note"]  # personal: the pro and the client
    actions_detail = ["cancel_detail"]

    def get_readonly_fields(self, request, obj=None):
        hidden = set(self.exclude)
        return [f.name for f in self.model._meta.fields if f.name not in hidden] + ["payment_link"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @display(description=_("status"), ordering="status", label=STATUS_LABELS)
    def status_badge(self, appointment):
        return appointment.status, appointment.get_status_display()

    @display(description=_("deposit"))
    def deposit(self, appointment):
        return amount(appointment.deposit_minor, appointment.currency)

    @display(description=_("payment"))
    def payment_link(self, appointment):
        if not appointment.payment_id:
            return "—"
        url = reverse("admin:payments_payment_change", args=[appointment.payment_id])
        return format_html('<a href="{}">{}</a>', url, appointment.payment.reference)

    @action(description=_("Cancel and refund"), url_path="cancel", icon="event_busy")
    def cancel_detail(self, request, object_id):
        appointment = get_object_or_404(Appointment, pk=object_id)
        try:
            appointments.cancel(appointment, by=Appointment.CancelledBy.SYSTEM, actor=request.user)
        except DomainError as exc:
            self.message_user(request, exc.text(), messages.ERROR)
        else:
            self.message_user(request, _("Cancelled; the client is refunded and told."))
        return redirect(reverse("admin:booking_appointment_change", args=[object_id]))


class PeriodInline(TabularInline):
    model = StaffPeriod
    fields = ["weekday", "starts_at", "ends_at"]
    extra = 0
    tab = True


class BreakInline(TabularInline):
    model = StaffBreak
    fields = ["weekday", "starts_at", "ends_at"]
    extra = 0
    tab = True


@admin.register(StaffMember)
class StaffMemberAdmin(AuditedModelAdmin):
    list_display = ["name", "pro", "is_owner", "has_account", "own_hours", "is_active"]
    list_filter = ["is_owner", "own_hours", "is_active"]
    search_fields = ["name", "pro__business_name", "pro__slug"]
    autocomplete_fields = ["user"]
    readonly_fields = ["pro", "is_owner", "invited_at"]
    fields = [
        "pro",
        "name",
        "color",
        "is_owner",
        "user",
        "invited_at",
        "daily_limit",
        "own_hours",
        "is_active",
        "position",
    ]
    inlines = [PeriodInline, BreakInline]

    def has_add_permission(self, request):
        return False

    @display(description=_("account"), boolean=True)
    def has_account(self, staff):
        return staff.user_id is not None


@admin.register(BookingSettings)
class BookingSettingsAdmin(AuditedModelAdmin):
    list_display = ["pro", "auto_confirm", "slot_step_minutes", "accepts_guests"]
    list_filter = ["auto_confirm", "accepts_guests"]
    search_fields = ["pro__business_name", "pro__slug"]
    readonly_fields = ["pro"]
    exclude = ["ical_token"]

    def has_add_permission(self, request):
        return False


@admin.register(TimeOff)
class TimeOffAdmin(AuditedModelAdmin):
    list_display = ["pro", "staff", "kind", "starts_at", "ends_at", "note"]
    list_filter = ["kind"]
    search_fields = ["pro__business_name", "note"]
    date_hierarchy = "starts_at"
    readonly_fields = ["pro", "staff"]

    def has_add_permission(self, request):
        return False


@admin.register(Resource)
class ResourceAdmin(AuditedModelAdmin):
    list_display = ["name", "pro", "quantity", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "pro__business_name"]
    readonly_fields = ["pro"]

    def has_add_permission(self, request):
        return False


@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(ReadOnlyMixin, AuditedModelAdmin):
    list_display = ["pro", "service", "day", "who", "status", "offer_expires_at"]
    list_filter = ["status"]
    search_fields = ["pro__business_name"]
    date_hierarchy = "day"
    exclude = ["guest"]

    @display(description=_("client"))
    def who(self, entry):
        if entry.client_id:
            return entry.client.first_name
        return entry.guest.first_name if entry.guest_id else "—"


class GroupAppointmentInline(ReadOnlyMixin, TabularInline):
    model = Appointment
    fields = ["reference", "client_name", "starts_at", "status", "deposit_minor"]
    readonly_fields = fields
    extra = 0
    tab = True
    show_change_link = True

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(GroupBooking)
class GroupBookingAdmin(ReadOnlyMixin, AuditedModelAdmin):
    list_display = ["title", "pro", "organizer", "status", "pay_by", "created_at"]
    list_filter = ["status"]
    search_fields = ["title", "pro__business_name"]
    exclude = ["share_token"]
    inlines = [GroupAppointmentInline]


@admin.register(ClientRecord)
class ClientRecordAdmin(ReadOnlyMixin, AuditedModelAdmin):
    """Who is in which client file (to answer deletion requests). Notes stay private."""

    list_display = ["name", "pro", "has_account", "updated_at"]
    search_fields = ["name", "pro__business_name"]
    fields = ["pro", "name", "client", "updated_at"]
    readonly_fields = fields

    @display(description=_("account"), boolean=True)
    def has_account(self, record):
        return record.client_id is not None


@admin.register(LastMinuteOffer)
class LastMinuteOfferAdmin(AuditedModelAdmin):
    list_display = ["pro", "percent_off", "window_hours", "is_active", "announced_at"]
    list_filter = ["is_active"]
    search_fields = ["pro__business_name"]
    readonly_fields = ["pro", "announced_at"]

    def has_add_permission(self, request):
        return False
