"""What the web app gets from bookings, and what it sends."""

from __future__ import annotations

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from apps.core.media.api import MediaSerializer
from apps.core.media.services import asset_payload
from apps.pros.hours import zone_of
from apps.pros.models import Service

from . import availability
from .models import Appointment, BookingSettings, StaffMember, TimeOff, WaitlistEntry
from .services import appointments as appointment_services
from .services import common

A = Appointment.Status


def _iso(value):
    return value.isoformat() if value else None


def _ready(asset):
    return asset_payload(asset) if asset is not None and asset.is_ready else None


def _time(value):
    return value.strftime("%H:%M") if value else None


# --- The pro, her services and her people -------------------------------------------------------


def pro_brief(pro) -> dict:
    receives = pro.receives_clients
    return {
        "id": str(pro.pk),
        "slug": pro.slug,
        "name": pro.display_name,
        "photo": _ready(pro.photo),
        "city": pro.city,
        "district": pro.district if receives else "",
        "address": pro.address if receives else "",
        "is_verified": pro.is_verified,
        "rating_average": float(pro.rating_average) if pro.rating_average is not None else None,
        "rating_count": pro.rating_count,
        "timezone": str(zone_of(pro)),
    }


class BookingProSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    slug = serializers.CharField(allow_null=True)
    name = serializers.CharField()
    photo = MediaSerializer(allow_null=True)
    city = serializers.CharField(allow_blank=True)
    district = serializers.CharField(allow_blank=True)
    address = serializers.CharField(allow_blank=True)
    is_verified = serializers.BooleanField()
    rating_average = serializers.FloatField(allow_null=True)
    rating_count = serializers.IntegerField()
    timezone = serializers.CharField()


def service_payload(service: Service, *, forced_percent: int = 0) -> dict:
    price = service.price_minor
    work = sum(s.duration_minutes for s in service.steps.all() if s.kind == "work")
    return {
        "id": str(service.pk),
        "name": service.name,
        "description": service.description,
        "price_kind": service.price_kind,
        "price_minor": price,
        "currency": service.currency,
        "duration_minutes": service.duration_minutes,
        "work_minutes": work or service.duration_minutes,
        "deposit_minor": appointment_services.deposit_of(
            service, price, forced_percent=forced_percent
        ),
        "category_id": str(service.category_id) if service.category_id else None,
        "options": [
            {
                "id": str(o.pk),
                "name": o.name,
                "price_minor": o.price_minor,
                "extra_minutes": o.extra_minutes,
            }
            for o in service.options.all()
        ],
    }


class BookingOptionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    price_minor = serializers.IntegerField()
    extra_minutes = serializers.IntegerField()


class BookableServiceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    price_kind = serializers.CharField()
    price_minor = serializers.IntegerField(allow_null=True)
    currency = serializers.CharField()
    duration_minutes = serializers.IntegerField()
    work_minutes = serializers.IntegerField()
    deposit_minor = serializers.IntegerField()
    category_id = serializers.UUIDField(allow_null=True)
    options = BookingOptionSerializer(many=True)


def staff_brief(staff: StaffMember) -> dict:
    photo = staff.user.photo if staff.user_id and staff.user.photo_id else None
    return {
        "id": str(staff.pk),
        "name": staff.name,
        "color": staff.color,
        "photo": _ready(photo),
        "service_ids": [str(s.pk) for s in staff.services.all()],
    }


class StaffBriefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    color = serializers.CharField()
    photo = MediaSerializer(allow_null=True)
    service_ids = serializers.ListField(child=serializers.UUIDField())


class LastMinuteSerializer(serializers.Serializer):
    percent_off = serializers.IntegerField()
    window_hours = serializers.IntegerField()
    is_active = serializers.BooleanField()


def last_minute_payload(pro) -> dict | None:
    try:
        offer = pro.last_minute
    except Exception:
        return None
    return {
        "percent_off": offer.percent_off,
        "window_hours": offer.window_hours,
        "is_active": offer.is_active,
    }


class BookingPageSerializer(serializers.Serializer):
    pro = BookingProSerializer()
    services = BookableServiceSerializer(many=True)
    staff = StaffBriefSerializer(many=True)
    accepts_guests = serializers.BooleanField()
    auto_confirm = serializers.BooleanField()
    free_cancel_hours = serializers.IntegerField()
    last_minute = LastMinuteSerializer(allow_null=True)
    first_day = serializers.DateField()
    last_day = serializers.DateField()


# --- Slots ----------------------------------------------------------------------------------------


def slot_payload(slot: availability.Slot) -> dict:
    return {
        "start": _iso(slot.start),
        "end": _iso(slot.end),
        "staff_id": slot.staff_id,
        "discount_percent": slot.discount_percent,
    }


class SlotSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    staff_id = serializers.UUIDField(allow_null=True)
    discount_percent = serializers.IntegerField()


class SlotDaySerializer(serializers.Serializer):
    day = serializers.DateField()
    slots = SlotSerializer(many=True)


class SlotsSerializer(serializers.Serializer):
    days = SlotDaySerializer(many=True)
    next_day = serializers.DateField(allow_null=True)


class SlotsQuerySerializer(serializers.Serializer):
    service = serializers.UUIDField()
    day = serializers.DateField(required=False)
    days = serializers.IntegerField(required=False, min_value=1, max_value=14, default=7)
    staff = serializers.UUIDField(required=False)
    options = serializers.CharField(required=False, allow_blank=True)

    def validate_options(self, value):
        import uuid

        try:
            return [uuid.UUID(v) for v in value.split(",") if v]
        except ValueError as exc:
            raise serializers.ValidationError("invalid") from exc


# --- Appointments ---------------------------------------------------------------------------------


def step_payload(step) -> dict:
    return {
        "position": step.position,
        "kind": step.kind,
        "label": step.label,
        "starts_at": _iso(step.starts_at),
        "ends_at": _iso(step.ends_at),
        "staff_id": str(step.staff_id) if step.staff_id else None,
        "staff_name": step.staff.name if step.staff_id else "",
        "resource_id": str(step.resource_id) if step.resource_id else None,
    }


class AppointmentStepSerializer(serializers.Serializer):
    position = serializers.IntegerField()
    kind = serializers.CharField()
    label = serializers.CharField(allow_blank=True)
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    staff_id = serializers.UUIDField(allow_null=True)
    staff_name = serializers.CharField(allow_blank=True)
    resource_id = serializers.UUIDField(allow_null=True)


class AdviceSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    title = serializers.CharField()
    slug = serializers.CharField()
    note = serializers.CharField(allow_blank=True)


class AppointmentPaymentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    total_minor = serializers.IntegerField()
    checkout_url = serializers.CharField(allow_blank=True)


def _payment(appointment: Appointment, *, buyer: bool) -> dict | None:
    payment = appointment.payment
    if payment is None:
        return None
    return {
        "id": str(payment.pk),
        "status": payment.status,
        "total_minor": payment.total_minor,
        "checkout_url": payment.checkout_url if buyer else "",
    }


def appointment_payload(appointment: Appointment, *, side: str, viewer=None) -> dict:
    """`side`: client (her own, or a guest with her link) or pro (the agenda)."""
    is_client = side == "client"
    now = timezone.now()
    steps = sorted(appointment.steps.all(), key=lambda s: s.position)
    free_until = appointment_services.free_cancellation_until(appointment)
    done = appointment.status == A.COMPLETED
    advice = [
        {
            "product_id": str(r.product_id),
            "title": r.product.title,
            "slug": r.product.slug,
            "note": r.note,
        }
        for r in appointment.recommendations.all()
    ]
    return {
        "id": str(appointment.pk),
        "reference": appointment.reference,
        "status": appointment.status,
        "source": appointment.source,
        "pro": pro_brief(appointment.pro),
        "service_id": str(appointment.service_id),
        "service_name": appointment.service.name,
        "option_names": [o.name for o in appointment.options.all()],
        "starts_at": _iso(appointment.starts_at),
        "ends_at": _iso(appointment.ends_at),
        "client_id": str(appointment.client_id) if appointment.client_id else None,
        "client_name": appointment.client_name,
        "client_phone": "" if is_client else appointment.client_phone,
        "is_guest": appointment.client_id is None,
        "price_minor": appointment.price_minor,
        "currency": appointment.currency,
        "discount_percent": appointment.discount_percent,
        "deposit_minor": appointment.deposit_minor,
        "payment": _payment(appointment, buyer=is_client),
        "note": appointment.note,
        "pro_message": appointment.pro_message,
        "proposed_from": _iso(appointment.proposed_from),
        "answer_due_at": _iso(appointment.answer_due_at),
        "group_id": str(appointment.group_id) if appointment.group_id else None,
        "steps": [step_payload(s) for s in steps],
        "free_cancel_until": _iso(free_until),
        "late_cancel": now > free_until,
        "can_cancel": appointment.status in Appointment.BLOCKING,
        "can_review": is_client and done and appointment.client_id is not None,
        "advice": advice,
        "photos": [_ready(p.media) for p in appointment.photos.all() if p.media.is_ready]
        if not is_client or done
        else [],
        "created_at": _iso(appointment.created_at),
    }


class AppointmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    reference = serializers.CharField()
    status = serializers.ChoiceField(choices=A.choices)
    source = serializers.ChoiceField(choices=Appointment.Source.choices)
    pro = BookingProSerializer()
    service_id = serializers.UUIDField()
    service_name = serializers.CharField()
    option_names = serializers.ListField(child=serializers.CharField())
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    client_id = serializers.UUIDField(allow_null=True)
    client_name = serializers.CharField()
    client_phone = serializers.CharField(allow_blank=True)
    is_guest = serializers.BooleanField()
    price_minor = serializers.IntegerField(allow_null=True)
    currency = serializers.CharField()
    discount_percent = serializers.IntegerField()
    deposit_minor = serializers.IntegerField()
    payment = AppointmentPaymentSerializer(allow_null=True)
    note = serializers.CharField(allow_blank=True)
    pro_message = serializers.CharField(allow_blank=True)
    proposed_from = serializers.DateTimeField(allow_null=True)
    answer_due_at = serializers.DateTimeField(allow_null=True)
    group_id = serializers.UUIDField(allow_null=True)
    steps = AppointmentStepSerializer(many=True)
    free_cancel_until = serializers.DateTimeField()
    late_cancel = serializers.BooleanField()
    can_cancel = serializers.BooleanField()
    can_review = serializers.BooleanField()
    advice = AdviceSerializer(many=True)
    photos = MediaSerializer(many=True)
    created_at = serializers.DateTimeField()


class BookedSerializer(serializers.Serializer):
    appointment = AppointmentSerializer()
    manage_url = serializers.CharField(allow_null=True)
    checkout_url = serializers.CharField(allow_null=True)


def booked_payload(appointment: Appointment, *, guest: bool) -> dict:
    payment = appointment.payment
    return {
        "appointment": appointment_payload(appointment, side="client"),
        "manage_url": common.manage_link(appointment) if guest else None,
        "checkout_url": payment.checkout_url
        if payment is not None and payment.checkout_url
        else None,
    }


class BookInputSerializer(serializers.Serializer):
    service_id = serializers.UUIDField()
    start = serializers.DateTimeField()
    staff_id = serializers.UUIDField(required=False, allow_null=True)
    option_ids = serializers.ListField(child=serializers.UUIDField(), required=False, max_length=10)
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)
    guest_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    guest_phone = serializers.CharField(required=False, allow_blank=True, max_length=32)
    post_id = serializers.UUIDField(required=False, allow_null=True)
    gift_card_code = serializers.CharField(required=False, allow_blank=True, max_length=20)
    marketing_consent = serializers.BooleanField(required=False, default=False)


class CancelInputSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=300)


class AnswerInputSerializer(serializers.Serializer):
    accept = serializers.BooleanField()


class MessageInputSerializer(serializers.Serializer):
    message = serializers.CharField(required=False, allow_blank=True, max_length=500)


class ProposeInputSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    message = serializers.CharField(required=False, allow_blank=True, max_length=500)


class MoveInputSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    staff_id = serializers.UUIDField(required=False, allow_null=True)


class AppointmentListSerializer(serializers.Serializer):
    upcoming = AppointmentSerializer(many=True)
    past = AppointmentSerializer(many=True)


# --- Waiting list and groups ----------------------------------------------------------------------


def waitlist_payload(entry: WaitlistEntry) -> dict:
    return {
        "id": str(entry.pk),
        "pro": pro_brief(entry.pro),
        "service_name": entry.service.name,
        "day": entry.day.isoformat(),
        "from_time": _time(entry.from_time),
        "to_time": _time(entry.to_time),
        "status": entry.status,
        "offer_id": str(entry.offer_id) if entry.offer_id else None,
        "offer_expires_at": _iso(entry.offer_expires_at),
    }


class WaitlistEntrySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    pro = BookingProSerializer()
    service_name = serializers.CharField()
    day = serializers.DateField()
    from_time = serializers.CharField(allow_null=True)
    to_time = serializers.CharField(allow_null=True)
    status = serializers.ChoiceField(choices=WaitlistEntry.Status.choices)
    offer_id = serializers.UUIDField(allow_null=True)
    offer_expires_at = serializers.DateTimeField(allow_null=True)


class WaitlistInputSerializer(serializers.Serializer):
    service_id = serializers.UUIDField()
    day = serializers.DateField()
    staff_id = serializers.UUIDField(required=False, allow_null=True)
    from_time = serializers.TimeField(required=False, allow_null=True)
    to_time = serializers.TimeField(required=False, allow_null=True)
    guest_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    guest_phone = serializers.CharField(required=False, allow_blank=True, max_length=32)


class GroupInputSerializer(serializers.Serializer):
    service_id = serializers.UUIDField()
    start = serializers.DateTimeField()
    size = serializers.IntegerField(min_value=2, max_value=50)
    title = serializers.CharField(required=False, allow_blank=True, max_length=80)


def group_payload(group, viewer) -> dict:
    rows = sorted(group.appointments.all(), key=lambda a: (a.starts_at, a.created_at))
    first = rows[0] if rows else None
    return {
        "id": str(group.pk),
        "title": group.title,
        "status": group.status,
        "pay_by": _iso(group.pay_by),
        "share_url": f"/rdv/groupe/{group.share_token}",
        "is_organizer": viewer is not None and group.organizer_id == viewer.pk,
        "organizer_name": group.organizer.first_name,
        "pro": pro_brief(group.pro),
        "service_name": first.service.name if first else "",
        "currency": first.currency if first else "",
        "share_minor": first.deposit_minor if first else 0,
        "places": [
            {
                "id": str(a.pk),
                "starts_at": _iso(a.starts_at),
                "status": a.status,
                "taken": a.client_id is not None,
                "mine": viewer is not None and a.client_id == viewer.pk,
                "paid": a.status == A.CONFIRMED,
            }
            for a in rows
        ],
    }


class GroupPlaceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    starts_at = serializers.DateTimeField()
    status = serializers.CharField()
    taken = serializers.BooleanField()
    mine = serializers.BooleanField()
    paid = serializers.BooleanField()


class GroupSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField(allow_blank=True)
    status = serializers.CharField()
    pay_by = serializers.DateTimeField(allow_null=True)
    share_url = serializers.CharField()
    is_organizer = serializers.BooleanField()
    organizer_name = serializers.CharField(allow_blank=True)
    pro = BookingProSerializer()
    service_name = serializers.CharField()
    currency = serializers.CharField(allow_blank=True)
    share_minor = serializers.IntegerField()
    places = GroupPlaceSerializer(many=True)


class GroupShareInputSerializer(serializers.Serializer):
    place_id = serializers.UUIDField(required=False, allow_null=True)


class CheckoutSerializer(serializers.Serializer):
    checkout_url = serializers.CharField()


# --- The agenda -----------------------------------------------------------------------------------


def staff_payload(staff: StaffMember) -> dict:
    return {
        **staff_brief(staff),
        "phone": str(staff.phone or ""),
        "is_owner": staff.is_owner,
        "is_active": staff.is_active,
        "has_account": staff.user_id is not None,
        "daily_limit": staff.daily_limit,
        "own_hours": staff.own_hours,
        "periods": [
            {"weekday": p.weekday, "starts_at": _time(p.starts_at), "ends_at": _time(p.ends_at)}
            for p in staff.periods.all()
        ],
        "breaks": [
            {"weekday": p.weekday, "starts_at": _time(p.starts_at), "ends_at": _time(p.ends_at)}
            for p in staff.breaks.all()
        ],
    }


class HoursRowSerializer(serializers.Serializer):
    weekday = serializers.IntegerField(min_value=0, max_value=6)
    starts_at = serializers.TimeField(format="%H:%M")
    ends_at = serializers.TimeField(format="%H:%M")


class StaffSerializer(StaffBriefSerializer):
    phone = serializers.CharField(allow_blank=True)
    is_owner = serializers.BooleanField()
    is_active = serializers.BooleanField()
    has_account = serializers.BooleanField()
    daily_limit = serializers.IntegerField(allow_null=True)
    own_hours = serializers.BooleanField()
    periods = HoursRowSerializer(many=True)
    breaks = HoursRowSerializer(many=True)


class StaffInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80)
    color = serializers.CharField(max_length=7, required=False)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    service_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    daily_limit = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, max_value=50
    )
    own_hours = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)


class StaffHoursInputSerializer(serializers.Serializer):
    periods = HoursRowSerializer(many=True, required=False)
    breaks = HoursRowSerializer(many=True, required=False)


def time_off_payload(off: TimeOff) -> dict:
    return {
        "id": str(off.pk),
        "staff_id": str(off.staff_id) if off.staff_id else None,
        "kind": off.kind,
        "starts_at": _iso(off.starts_at),
        "ends_at": _iso(off.ends_at),
        "note": off.note,
    }


class TimeOffSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    staff_id = serializers.UUIDField(allow_null=True)
    kind = serializers.ChoiceField(choices=TimeOff.Kind.choices)
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    note = serializers.CharField(allow_blank=True)


class TimeOffInputSerializer(serializers.Serializer):
    staff_id = serializers.UUIDField(required=False, allow_null=True)
    kind = serializers.ChoiceField(choices=TimeOff.Kind.choices, required=False)
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    note = serializers.CharField(required=False, allow_blank=True, max_length=120)


class ResourceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    quantity = serializers.IntegerField()


class ResourceInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=60)
    quantity = serializers.IntegerField(min_value=1, max_value=50)


class OpeningSerializer(serializers.Serializer):
    weekday = serializers.IntegerField()
    opens_at = serializers.CharField()
    closes_at = serializers.CharField()


class AgendaSerializer(serializers.Serializer):
    pro = BookingProSerializer()
    can_manage = serializers.BooleanField()
    staff = StaffSerializer(many=True)
    opening = OpeningSerializer(many=True)
    appointments = AppointmentSerializer(many=True)
    time_off = TimeOffSerializer(many=True)
    pending_count = serializers.IntegerField()
    pending = AppointmentSerializer(many=True)
    services = BookableServiceSerializer(many=True)
    slot_step_minutes = serializers.IntegerField()


class AgendaQuerySerializer(serializers.Serializer):
    start = serializers.DateField()
    days = serializers.IntegerField(min_value=1, max_value=7, default=1)
    staff = serializers.UUIDField(required=False)
    pro = serializers.UUIDField(required=False)


class QuickBookInputSerializer(serializers.Serializer):
    service_id = serializers.UUIDField()
    start = serializers.DateTimeField()
    staff_id = serializers.UUIDField(required=False, allow_null=True)
    option_ids = serializers.ListField(child=serializers.UUIDField(), required=False, max_length=10)
    client_name = serializers.CharField(max_length=150)
    client_phone = serializers.CharField(max_length=32)
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


def settings_payload(pro, booking_settings: BookingSettings) -> dict:
    base = settings.SHORT_LINK_BASE_URL.rstrip("/")
    site = settings.SITE_URL.rstrip("/")
    return {
        "auto_confirm": booking_settings.auto_confirm,
        "slot_step_minutes": booking_settings.slot_step_minutes,
        "min_notice_minutes": booking_settings.min_notice_minutes,
        "horizon_days": booking_settings.horizon_days,
        "free_cancel_hours": booking_settings.free_cancel_hours,
        "late_tolerance_minutes": booking_settings.late_tolerance_minutes,
        "accepts_guests": booking_settings.accepts_guests,
        "defaults": {
            "min_notice_minutes": int(common.setting("booking.min_notice_minutes", pro, 120)),
            "horizon_days": int(common.setting("booking.horizon_days", pro, 60)),
            "free_cancel_hours": int(common.setting("booking.free_cancel_hours", pro, 24)),
            "late_tolerance_minutes": int(
                common.setting("booking.late_tolerance_minutes", pro, 15)
            ),
        },
        "booking_url": f"{base}/{pro.slug}/rdv" if pro.slug else "",
        "ical_url": f"{site}/api/v1/agenda/{booking_settings.ical_token}.ics",
        "last_minute": last_minute_payload(pro),
        "resources": [
            {"id": str(r.pk), "name": r.name, "quantity": r.quantity}
            for r in pro.resources.filter(is_active=True).order_by("name")
        ],
    }


class SettingsDefaultsSerializer(serializers.Serializer):
    min_notice_minutes = serializers.IntegerField()
    horizon_days = serializers.IntegerField()
    free_cancel_hours = serializers.IntegerField()
    late_tolerance_minutes = serializers.IntegerField()


class AgendaSettingsSerializer(serializers.Serializer):
    auto_confirm = serializers.BooleanField()
    slot_step_minutes = serializers.IntegerField()
    min_notice_minutes = serializers.IntegerField(allow_null=True)
    horizon_days = serializers.IntegerField(allow_null=True)
    free_cancel_hours = serializers.IntegerField(allow_null=True)
    late_tolerance_minutes = serializers.IntegerField(allow_null=True)
    accepts_guests = serializers.BooleanField()
    defaults = SettingsDefaultsSerializer()
    booking_url = serializers.CharField(allow_blank=True)
    ical_url = serializers.CharField()
    last_minute = LastMinuteSerializer(allow_null=True)
    resources = ResourceSerializer(many=True)


class AgendaSettingsInputSerializer(serializers.Serializer):
    auto_confirm = serializers.BooleanField(required=False)
    slot_step_minutes = serializers.IntegerField(required=False, min_value=5, max_value=60)
    min_notice_minutes = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    horizon_days = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, max_value=365
    )
    free_cancel_hours = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=168
    )
    late_tolerance_minutes = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=120
    )
    accepts_guests = serializers.BooleanField(required=False)


class LastMinuteInputSerializer(serializers.Serializer):
    percent_off = serializers.IntegerField(min_value=5, max_value=70)
    window_hours = serializers.IntegerField(min_value=1, max_value=72)
    is_active = serializers.BooleanField()


# --- Client files ---------------------------------------------------------------------------------


def record_payload(record, *, history=None) -> dict:
    data = {
        "id": str(record.pk),
        "name": record.name,
        "phone": str(record.phone or (record.client.phone if record.client_id else "") or ""),
        "has_account": record.client_id is not None,
        "notes": record.notes,
        "preferences": record.preferences,
        "updated_at": _iso(record.updated_at),
    }
    if history is not None:
        data["history"] = [appointment_payload(a, side="pro") for a in history]
    return data


class ClientRecordSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    phone = serializers.CharField(allow_blank=True)
    has_account = serializers.BooleanField()
    notes = serializers.CharField(allow_blank=True)
    preferences = serializers.CharField(allow_blank=True)
    updated_at = serializers.DateTimeField()


class ClientRecordDetailSerializer(ClientRecordSerializer):
    history = AppointmentSerializer(many=True)


class ClientRecordInputSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    preferences = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class PhotoInputSerializer(serializers.Serializer):
    media_id = serializers.UUIDField()


class AdviceInputSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    note = serializers.CharField(required=False, allow_blank=True, max_length=300)


class AppointmentDetailSerializer(serializers.Serializer):
    appointment = AppointmentSerializer()
    record = ClientRecordSerializer(allow_null=True)
    no_shows = serializers.IntegerField()
