from __future__ import annotations

import datetime
import io

from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttling import SettingRateThrottle
from apps.accounts.views_base import OptionalAuthView
from apps.core.selectors import is_feature_enabled
from apps.payments import services as payment_services
from apps.pros.hours import zone_of
from apps.pros.models import ProProfile
from apps.pros.selectors import visible_services

from . import availability, errors, selectors
from . import serializers as s
from .models import (
    Appointment,
    BookingSettings,
    ClientRecord,
    GroupBooking,
    Resource,
    StaffMember,
    TimeOff,
    WaitlistEntry,
)
from .services import agenda, appointments, common, groups, waitlist

A = Appointment.Status


def _signed_in(request):
    user = request.user
    return user if user is not None and user.is_authenticated else None


def _published(slug) -> ProProfile:
    pro = (
        ProProfile.objects.filter(slug=slug, status=ProProfile.Status.PUBLISHED)
        .select_related("user", "photo", "country")
        .first()
    )
    if pro is None or not is_feature_enabled("booking", country=pro.country):
        raise errors.ProNotFound()
    return pro


def _services(pro):
    return list(visible_services().filter(pro=pro))


def _staff(pro):
    return list(
        StaffMember.objects.filter(pro=pro, is_active=True)
        .select_related("user__photo")
        .prefetch_related("services", "periods", "breaks")
        .order_by("-is_owner", "position", "name")
    )


class BookingWriteView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "booking"

    def get_throttles(self):
        return super().get_throttles() if self.request.method != "GET" else []


# --- Public: the booking page of a pro ------------------------------------------------------------


class BookingPageView(OptionalAuthView):
    """Services, people and rules of a pro (the page « Book » of her showcase)."""

    throttle_classes = [SettingRateThrottle]

    def get_throttles(self):
        self.throttle_scope = "search" if self.request.method == "GET" else "booking"
        return super().get_throttles()

    @extend_schema(tags=["booking"], responses=s.BookingPageSerializer)
    def get(self, request, slug):
        pro = _published(slug)
        user = _signed_in(request)
        forced = appointments.forced_deposit_percent(pro, user=user) if user else 0
        booking_settings = common.settings_of(pro)
        selectors.owner_staff(pro)
        today = timezone.now().astimezone(zone_of(pro)).date()
        return Response(
            {
                "pro": s.pro_brief(pro),
                "services": [s.service_payload(x, forced_percent=forced) for x in _services(pro)],
                "staff": [s.staff_brief(m) for m in _staff(pro)],
                "accepts_guests": booking_settings.accepts_guests,
                "auto_confirm": booking_settings.auto_confirm,
                "free_cancel_hours": int(
                    common.setting(
                        "booking.free_cancel_hours", pro, 24, booking_settings.free_cancel_hours
                    )
                ),
                "last_minute": s.last_minute_payload(pro),
                "first_day": today.isoformat(),
                "last_day": (
                    today + datetime.timedelta(days=availability.horizon(pro))
                ).isoformat(),
            }
        )

    @extend_schema(
        tags=["booking"], request=s.BookInputSerializer, responses={201: s.BookedSerializer}
    )
    def post(self, request, slug):
        pro = _published(slug)
        data = s.BookInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        user = _signed_in(request)
        post = None
        if values.get("post_id"):
            from apps.social.models import Post

            post = Post.objects.filter(
                pk=values["post_id"], pro=pro, status=Post.Status.PUBLISHED
            ).first()
        booked = appointments.book(
            pro,
            values["service_id"],
            values["start"],
            user=user,
            guest_name=values.get("guest_name", ""),
            guest_phone=values.get("guest_phone", ""),
            staff_id=values.get("staff_id"),
            option_ids=values.get("option_ids", []),
            note=values.get("note", ""),
            source=Appointment.Source.LOOK if post else Appointment.Source.ONLINE,
            post=post,
            gift_card_code=values.get("gift_card_code", ""),
        )
        if values.get("marketing_consent"):
            from apps.salon.services.campaigns import set_consent

            client_record = agenda.record_for(pro, booked)
            for channel in ("email", "whatsapp"):
                set_consent(client_record, channel, True, source="booking")
        if booked.status == A.AWAITING_DEPOSIT:
            payment_services.start_checkout(booked.payment, buyer=user)
            booked.payment.refresh_from_db()
        fresh = selectors.appointment_by_id(booked.pk)
        return Response(s.booked_payload(fresh, guest=user is None), status=status.HTTP_201_CREATED)


class SlotsView(OptionalAuthView):
    """Free times of a service, day by day (7 days from `day`)."""

    @extend_schema(
        tags=["booking"],
        parameters=[s.SlotsQuerySerializer],
        responses=s.SlotsSerializer,
    )
    def get(self, request, slug):
        pro = _published(slug)
        query = s.SlotsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        values = query.validated_data
        service = appointments._service(pro, values["service"])
        staff_id = values.get("staff")
        if staff_id:
            appointments._staff(pro, staff_id, service)
        today = timezone.now().astimezone(zone_of(pro)).date()
        first = max(values.get("day") or today, today)
        last = today + datetime.timedelta(days=availability.horizon(pro))
        days = []
        for offset in range(values["days"]):
            day = first + datetime.timedelta(days=offset)
            if day > last:
                break
            found = availability.day_slots(
                pro, service, day, staff_id=staff_id, option_ids=values.get("options") or ()
            )
            days.append({"day": day.isoformat(), "slots": [s.slot_payload(x) for x in found]})
        following = first + datetime.timedelta(days=values["days"])
        return Response(
            {"days": days, "next_day": following.isoformat() if following <= last else None}
        )


class WaitlistJoinView(OptionalAuthView):
    throttle_scope = "booking"

    @extend_schema(
        tags=["booking"],
        request=s.WaitlistInputSerializer,
        responses={201: s.WaitlistEntrySerializer},
    )
    def post(self, request, slug):
        pro = _published(slug)
        data = s.WaitlistInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        entry = waitlist.join(
            pro,
            values["service_id"],
            values["day"],
            user=_signed_in(request),
            guest_name=values.get("guest_name", ""),
            guest_phone=values.get("guest_phone", ""),
            from_time=values.get("from_time"),
            to_time=values.get("to_time"),
            staff_id=values.get("staff_id"),
        )
        return Response(s.waitlist_payload(entry), status=status.HTTP_201_CREATED)


class GroupCreateView(BookingWriteView):
    @extend_schema(
        tags=["booking"], request=s.GroupInputSerializer, responses={201: s.GroupSerializer}
    )
    def post(self, request, slug):
        pro = _published(slug)
        data = s.GroupInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        group = groups.create_group(
            request.user,
            pro,
            values["service_id"],
            values["start"],
            values["size"],
            title=values.get("title", ""),
        )
        return Response(
            s.group_payload(_group(group.share_token), request.user),
            status=status.HTTP_201_CREATED,
        )


def _group(token) -> GroupBooking:
    found = (
        GroupBooking.objects.select_related("pro__photo", "pro__country", "organizer")
        .prefetch_related("appointments__service")
        .filter(share_token=token)
        .first()
    )
    if found is None:
        raise errors.GroupNotFound()
    return found


class GroupView(OptionalAuthView):
    @extend_schema(tags=["booking"], responses=s.GroupSerializer)
    def get(self, request, token):
        return Response(s.group_payload(_group(token), _signed_in(request)))


class GroupShareView(BookingWriteView):
    """A member takes a place of the group and pays its share (the organiser: the rest)."""

    @extend_schema(
        tags=["booking"], request=s.GroupShareInputSerializer, responses=s.CheckoutSerializer
    )
    def post(self, request, token):
        group = _group(token)
        data = s.GroupShareInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        share = groups.claim_share(group, request.user, data.validated_data.get("place_id"))
        payment = payment_services.start_checkout(share.payment, buyer=request.user)
        return Response({"checkout_url": payment.checkout_url})


# --- The client: her appointments, or a guest with her link ---------------------------------------


class ClientAppointmentsView(BookingWriteView):
    @extend_schema(
        tags=["booking"],
        operation_id="booking_my_appointments",
        responses=s.AppointmentListSerializer,
    )
    def get(self, request):
        now = timezone.now()
        rows = list(selectors.client_appointments(request.user)[:100])
        upcoming = [a for a in rows if a.ends_at >= now and a.status in Appointment.BLOCKING]
        past = [a for a in rows if a not in upcoming]
        return Response(
            {
                "upcoming": [s.appointment_payload(a, side="client") for a in reversed(upcoming)],
                "past": [s.appointment_payload(a, side="client") for a in past[:30]],
            }
        )


class ClientWaitlistView(BookingWriteView):
    @extend_schema(tags=["booking"], responses=s.WaitlistEntrySerializer(many=True))
    def get(self, request):
        rows = (
            WaitlistEntry.objects.filter(
                client=request.user,
                status__in=[WaitlistEntry.Status.WAITING, WaitlistEntry.Status.OFFERED],
            )
            .select_related("pro__photo", "pro__country", "service")
            .order_by("day")
        )
        return Response([s.waitlist_payload(e) for e in rows])


class ClientWaitlistEntryView(BookingWriteView):
    @extend_schema(tags=["booking"], request=None, responses={204: None})
    def delete(self, request, entry_id):
        entry = WaitlistEntry.objects.filter(pk=entry_id, client=request.user).first()
        if entry is None:
            raise errors.AppointmentNotFound()
        waitlist.leave(entry)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClientAppointmentBase(APIView):
    """An appointment of the signed-in client (by id) or of a guest (by her secret link)."""

    throttle_classes = [SettingRateThrottle]
    throttle_scope = "booking"

    def get_permissions(self):
        if "token" in self.kwargs:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_authenticators(self):
        from apps.accounts.authentication import (
            CookieJWTAuthentication,
            OptionalCookieJWTAuthentication,
        )

        if getattr(self, "swagger_fake_view", False):
            return [CookieJWTAuthentication()]
        return [OptionalCookieJWTAuthentication()]

    def get_throttles(self):
        return super().get_throttles() if self.request.method != "GET" else []

    def appointment(self, request, appointment_id=None, token=None) -> Appointment:
        if token is not None:
            found = appointments.by_token(token)
        else:
            selectors.claim_guest_appointments(request.user)
            found = Appointment.objects.filter(pk=appointment_id, client=request.user).first()
            if found is None:
                raise errors.AppointmentNotFound()
        return found

    def answer(self, appointment: Appointment) -> Response:
        return Response(
            s.appointment_payload(selectors.appointment_by_id(appointment.pk), side="client")
        )

    def actor(self, request):
        return _signed_in(request)


class ClientAppointmentView(ClientAppointmentBase):
    @extend_schema(tags=["booking"], responses=s.AppointmentSerializer)
    def get(self, request, appointment_id=None, token=None):
        return self.answer(self.appointment(request, appointment_id, token))


class ClientCancelView(ClientAppointmentBase):
    @extend_schema(
        tags=["booking"], request=s.CancelInputSerializer, responses=s.AppointmentSerializer
    )
    def post(self, request, appointment_id=None, token=None):
        found = self.appointment(request, appointment_id, token)
        appointments.cancel(found, by=Appointment.CancelledBy.CLIENT, actor=self.actor(request))
        return self.answer(found)


class ClientAnswerView(ClientAppointmentBase):
    """Yes or no to another time proposed by the pro."""

    @extend_schema(
        tags=["booking"], request=s.AnswerInputSerializer, responses=s.AppointmentSerializer
    )
    def post(self, request, appointment_id=None, token=None):
        found = self.appointment(request, appointment_id, token)
        data = s.AnswerInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        appointments.answer_proposal(
            found, accept=data.validated_data["accept"], actor=self.actor(request)
        )
        return self.answer(found)


class ClientAcceptOfferView(ClientAppointmentBase):
    """The waiting-list client takes the place kept for her."""

    @extend_schema(tags=["booking"], request=None, responses=s.BookedSerializer)
    def post(self, request, appointment_id=None, token=None):
        found = self.appointment(request, appointment_id, token)
        entry = WaitlistEntry.objects.filter(offer=found).first()
        if entry is None:
            raise errors.InvalidStep()
        held = waitlist.accept(entry, user=self.actor(request))
        if held.status == A.AWAITING_DEPOSIT:
            if self.actor(request) is None or held.client_id != request.user.pk:
                raise errors.SignInToPay()
            payment_services.start_checkout(held.payment, buyer=request.user)
        fresh = selectors.appointment_by_id(held.pk)
        return Response(s.booked_payload(fresh, guest=token is not None))


class ClientPayView(BookingWriteView):
    """The deposit's payment page again (the client left it before paying)."""

    @extend_schema(tags=["booking"], request=None, responses=s.CheckoutSerializer)
    def post(self, request, appointment_id):
        found = Appointment.objects.filter(pk=appointment_id, client=request.user).first()
        if found is None:
            raise errors.AppointmentNotFound()
        appointments.start_deposit_payment(found, request.user)
        found.payment.refresh_from_db()
        return Response({"checkout_url": found.payment.checkout_url})


# --- The agenda: the pro and her collaborators ----------------------------------------------------


class AgendaBase(BookingWriteView):
    manage_only = False

    def access(self, request, pro_id=None):
        pro, staff_ids = selectors.agenda_access(request.user, pro_id)
        if pro is None:
            raise errors.AgendaNotFound()
        if self.manage_only and staff_ids is not None:
            raise errors.ManagersOnly()
        selectors.owner_staff(pro)
        return pro, staff_ids

    def appointment(self, request, appointment_id) -> tuple[Appointment, ProProfile]:
        found = Appointment.objects.select_related("pro").filter(pk=appointment_id).first()
        if found is None:
            raise errors.AppointmentNotFound()
        pro, staff_ids = selectors.agenda_access(request.user, found.pro_id)
        if pro is None or (
            staff_ids is not None and not found.steps.filter(staff_id__in=staff_ids).exists()
        ):
            raise errors.AppointmentNotFound()
        return found, pro

    def detail(self, appointment: Appointment) -> Response:
        fresh = selectors.appointment_by_id(appointment.pk)
        record = (
            ClientRecord.objects.filter(pro=fresh.pro, client=fresh.client).first()
            if fresh.client_id
            else ClientRecord.objects.filter(
                pro=fresh.pro, client=None, phone=fresh.client_phone
            ).first()
        )
        return Response(
            {
                "appointment": s.appointment_payload(fresh, side="pro"),
                "record": s.record_payload(record) if record else None,
                "no_shows": selectors.no_shows(user=fresh.client, phone=fresh.client_phone),
            }
        )


class AgendaView(AgendaBase):
    @extend_schema(
        tags=["agenda"], parameters=[s.AgendaQuerySerializer], responses=s.AgendaSerializer
    )
    def get(self, request):
        query = s.AgendaQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        values = query.validated_data
        pro, staff_ids = self.access(request, values.get("pro"))
        zone = zone_of(pro)
        start = datetime.datetime.combine(values["start"], datetime.time.min, tzinfo=zone)
        end = start + datetime.timedelta(days=values["days"])
        shown = staff_ids
        if values.get("staff"):
            wanted = {values["staff"]}
            shown = wanted if staff_ids is None else (wanted & staff_ids) or staff_ids
        staff = [m for m in _staff(pro) if staff_ids is None or m.pk in staff_ids]
        rows = selectors.appointments_between(pro, start, end, staff_ids=shown).prefetch_related(
            "options", "photos__media", "recommendations__product"
        )
        pending = Appointment.objects.filter(
            pro=pro, status=A.PENDING, starts_at__gte=timezone.now()
        )
        if staff_ids is not None:
            pending = pending.filter(steps__staff_id__in=staff_ids).distinct()
        waiting = selectors.with_details(pending.order_by("starts_at"))[:20]
        return Response(
            {
                "pro": s.pro_brief(pro),
                "can_manage": staff_ids is None,
                "staff": [s.staff_payload(m) for m in staff],
                "opening": [
                    {
                        "weekday": p.weekday,
                        "opens_at": p.opens_at.strftime("%H:%M"),
                        "closes_at": p.closes_at.strftime("%H:%M"),
                    }
                    for p in pro.opening_periods.all().order_by("weekday", "opens_at")
                ],
                "appointments": [s.appointment_payload(a, side="pro") for a in rows],
                "time_off": [
                    s.time_off_payload(t)
                    for t in selectors.time_off_between(pro, start, end, staff_ids=shown)
                ],
                "pending_count": pending.count(),
                "pending": [s.appointment_payload(a, side="pro") for a in waiting],
                "services": [s.service_payload(x) for x in _services(pro)],
                "slot_step_minutes": common.settings_of(pro).slot_step_minutes,
            }
        )


class AgendaAppointmentsView(AgendaBase):
    """Quick booking from the agenda (a client on the phone, at the counter)."""

    @extend_schema(
        tags=["agenda"],
        request=s.QuickBookInputSerializer,
        responses={201: s.AppointmentDetailSerializer},
    )
    def post(self, request):
        pro, staff_ids = self.access(request)
        data = s.QuickBookInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        staff_id = values.get("staff_id")
        if staff_ids is not None:
            staff_id = next(iter(staff_ids))  # a collaborator books for herself
        booked = appointments.book(
            pro,
            values["service_id"],
            values["start"],
            guest_name=values["client_name"],
            guest_phone=values["client_phone"],
            staff_id=staff_id,
            option_ids=values.get("option_ids", []),
            note=values.get("note", ""),
            source=Appointment.Source.PHONE,
            by_pro=request.user,
        )
        response = self.detail(booked)
        response.status_code = status.HTTP_201_CREATED
        return response


class AgendaAppointmentView(AgendaBase):
    @extend_schema(tags=["agenda"], responses=s.AppointmentDetailSerializer)
    def get(self, request, appointment_id):
        found, _ = self.appointment(request, appointment_id)
        return self.detail(found)


class AgendaConfirmView(AgendaBase):
    @extend_schema(tags=["agenda"], request=None, responses=s.AppointmentDetailSerializer)
    def post(self, request, appointment_id):
        found, _ = self.appointment(request, appointment_id)
        appointments.confirm(found, actor=request.user)
        return self.detail(found)


class AgendaDeclineView(AgendaBase):
    @extend_schema(
        tags=["agenda"], request=s.MessageInputSerializer, responses=s.AppointmentDetailSerializer
    )
    def post(self, request, appointment_id):
        found, _ = self.appointment(request, appointment_id)
        data = s.MessageInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        appointments.decline(
            found, actor=request.user, message=data.validated_data.get("message", "")
        )
        return self.detail(found)


class AgendaProposeView(AgendaBase):
    @extend_schema(
        tags=["agenda"], request=s.ProposeInputSerializer, responses=s.AppointmentDetailSerializer
    )
    def post(self, request, appointment_id):
        found, _ = self.appointment(request, appointment_id)
        data = s.ProposeInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        appointments.propose(
            found,
            actor=request.user,
            start=data.validated_data["start"],
            message=data.validated_data.get("message", ""),
        )
        return self.detail(found)


class AgendaMoveView(AgendaBase):
    """Drag and drop: another time, or another person."""

    @extend_schema(
        tags=["agenda"], request=s.MoveInputSerializer, responses=s.AppointmentDetailSerializer
    )
    def post(self, request, appointment_id):
        found, pro = self.appointment(request, appointment_id)
        data = s.MoveInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        _, staff_ids = selectors.agenda_access(request.user, pro.pk)
        staff_id = data.validated_data.get("staff_id")
        if staff_ids is not None and staff_id and staff_id not in staff_ids:
            raise errors.ManagersOnly()
        appointments.move(
            found, actor=request.user, start=data.validated_data["start"], staff_id=staff_id
        )
        return self.detail(found)


class AgendaCompleteView(AgendaBase):
    @extend_schema(tags=["agenda"], request=None, responses=s.AppointmentDetailSerializer)
    def post(self, request, appointment_id):
        found, _ = self.appointment(request, appointment_id)
        appointments.complete(found, actor=request.user)
        return self.detail(found)


class AgendaNoShowView(AgendaBase):
    @extend_schema(tags=["agenda"], request=None, responses=s.AppointmentDetailSerializer)
    def post(self, request, appointment_id):
        found, _ = self.appointment(request, appointment_id)
        appointments.no_show(found, actor=request.user)
        return self.detail(found)


class AgendaCancelView(AgendaBase):
    @extend_schema(
        tags=["agenda"], request=s.CancelInputSerializer, responses=s.AppointmentDetailSerializer
    )
    def post(self, request, appointment_id):
        found, _ = self.appointment(request, appointment_id)
        appointments.cancel(found, by=Appointment.CancelledBy.PRO, actor=request.user)
        return self.detail(found)


class AgendaPhotoView(AgendaBase):
    """A picture of the result, kept in the client's file."""

    @extend_schema(
        tags=["agenda"], request=s.PhotoInputSerializer, responses=s.AppointmentDetailSerializer
    )
    def post(self, request, appointment_id):
        found, pro = self.appointment(request, appointment_id)
        data = s.PhotoInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        agenda.add_photo(pro, found, data.validated_data["media_id"], owner=request.user)
        return self.detail(found)


class AgendaAdviceView(AgendaBase):
    """A product of the pro's shop, advised after the appointment."""

    @extend_schema(
        tags=["agenda"], request=s.AdviceInputSerializer, responses=s.AppointmentDetailSerializer
    )
    def post(self, request, appointment_id):
        found, pro = self.appointment(request, appointment_id)
        data = s.AdviceInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        agenda.recommend(
            pro,
            found,
            data.validated_data["product_id"],
            note=data.validated_data.get("note", ""),
        )
        return self.detail(found)


class TimeOffView(AgendaBase):
    """Absences, holidays, blocked ranges (a collaborator: only her own)."""

    @extend_schema(
        tags=["agenda"], request=s.TimeOffInputSerializer, responses={201: s.TimeOffSerializer}
    )
    def post(self, request):
        pro, staff_ids = self.access(request)
        data = s.TimeOffInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        staff_id = values.get("staff_id")
        if staff_ids is not None:
            staff_id = next(iter(staff_ids))
        off = agenda.add_time_off(
            pro,
            staff_id=staff_id,
            starts_at=values["starts_at"],
            ends_at=values["ends_at"],
            kind=values.get("kind", TimeOff.Kind.BLOCK),
            note=values.get("note", ""),
        )
        return Response(s.time_off_payload(off), status=status.HTTP_201_CREATED)


class TimeOffItemView(AgendaBase):
    @extend_schema(tags=["agenda"], request=None, responses={204: None})
    def delete(self, request, time_off_id):
        pro, staff_ids = self.access(request)
        if (
            staff_ids is not None
            and not TimeOff.objects.filter(pk=time_off_id, staff_id__in=staff_ids).exists()
        ):
            raise errors.ManagersOnly()
        agenda.remove_time_off(pro, time_off_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class StaffListView(AgendaBase):
    manage_only = True

    @extend_schema(tags=["agenda"], responses=s.StaffSerializer(many=True))
    def get(self, request):
        pro, _ = self.access(request)
        rows = (
            StaffMember.objects.filter(pro=pro)
            .select_related("user__photo")
            .prefetch_related("services", "periods", "breaks")
            .order_by("-is_owner", "position", "name")
        )
        return Response([s.staff_payload(m) for m in rows])

    @extend_schema(
        tags=["agenda"], request=s.StaffInputSerializer, responses={201: s.StaffSerializer}
    )
    def post(self, request):
        pro, _ = self.access(request)
        data = s.StaffInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        staff = agenda.save_staff(pro, **_staff_values(data.validated_data))
        return Response(s.staff_payload(_one_staff(staff.pk)), status=status.HTTP_201_CREATED)


def _staff_values(values: dict) -> dict:
    return {
        "name": values["name"],
        "color": values.get("color") or "#C8102E",
        "phone": values.get("phone", ""),
        "service_ids": values.get("service_ids"),
        "daily_limit": values.get("daily_limit"),
        "own_hours": values.get("own_hours", False),
        "is_active": values.get("is_active", True),
    }


def _one_staff(staff_id) -> StaffMember:
    return (
        StaffMember.objects.select_related("user__photo")
        .prefetch_related("services", "periods", "breaks")
        .get(pk=staff_id)
    )


class StaffItemView(AgendaBase):
    manage_only = True

    @extend_schema(tags=["agenda"], request=s.StaffInputSerializer, responses=s.StaffSerializer)
    def patch(self, request, staff_id):
        pro, _ = self.access(request)
        current = StaffMember.objects.filter(pk=staff_id, pro=pro).first()
        if current is None:
            raise errors.StaffNotFound()
        data = s.StaffInputSerializer(data={"name": current.name, **request.data})
        data.is_valid(raise_exception=True)
        values = {
            "name": current.name,
            "color": current.color,
            "phone": "",
            "service_ids": None,
            "daily_limit": current.daily_limit,
            "own_hours": current.own_hours,
            "is_active": current.is_active,
            **data.validated_data,
        }
        agenda.save_staff(pro, staff_id=current.pk, **_staff_values(values))
        return Response(s.staff_payload(_one_staff(current.pk)))


class StaffHoursView(AgendaBase):
    manage_only = True

    @extend_schema(
        tags=["agenda"], request=s.StaffHoursInputSerializer, responses=s.StaffSerializer
    )
    def put(self, request, staff_id):
        pro, _ = self.access(request)
        data = s.StaffHoursInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        for kind in ("periods", "breaks"):
            if kind in data.validated_data:
                agenda.set_hours(pro, staff_id, data.validated_data[kind], kind=kind)
        if not StaffMember.objects.filter(pk=staff_id, pro=pro).exists():
            raise errors.StaffNotFound()
        return Response(s.staff_payload(_one_staff(staff_id)))


class ResourcesView(AgendaBase):
    manage_only = True

    @extend_schema(
        tags=["agenda"], request=s.ResourceInputSerializer, responses={201: s.ResourceSerializer}
    )
    def post(self, request):
        pro, _ = self.access(request)
        data = s.ResourceInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        found = agenda.save_resource(pro, **data.validated_data)
        return Response(
            {"id": str(found.pk), "name": found.name, "quantity": found.quantity},
            status=status.HTTP_201_CREATED,
        )


class ResourceItemView(AgendaBase):
    manage_only = True

    @extend_schema(
        tags=["agenda"], request=s.ResourceInputSerializer, responses=s.ResourceSerializer
    )
    def patch(self, request, resource_id):
        pro, _ = self.access(request)
        data = s.ResourceInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        found = agenda.save_resource(pro, resource_id=resource_id, **data.validated_data)
        return Response({"id": str(found.pk), "name": found.name, "quantity": found.quantity})

    @extend_schema(tags=["agenda"], request=None, responses={204: None})
    def delete(self, request, resource_id):
        pro, _ = self.access(request)
        Resource.objects.filter(pk=resource_id, pro=pro).update(is_active=False)
        common.changed(pro)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AgendaSettingsView(AgendaBase):
    manage_only = True

    def answer(self, pro) -> Response:
        fresh = ProProfile.objects.get(pk=pro.pk)
        booking_settings = BookingSettings.objects.get_or_create(pro=fresh)[0]
        return Response(s.settings_payload(fresh, booking_settings))

    @extend_schema(tags=["agenda"], responses=s.AgendaSettingsSerializer)
    def get(self, request):
        pro, _ = self.access(request)
        return self.answer(pro)

    @extend_schema(
        tags=["agenda"],
        request=s.AgendaSettingsInputSerializer,
        responses=s.AgendaSettingsSerializer,
    )
    def patch(self, request):
        pro, _ = self.access(request)
        data = s.AgendaSettingsInputSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        agenda.update_settings(pro, **data.validated_data)
        return self.answer(pro)


class LastMinuteView(AgendaBase):
    manage_only = True

    @extend_schema(
        tags=["agenda"], request=s.LastMinuteInputSerializer, responses=s.LastMinuteSerializer
    )
    def put(self, request):
        pro, _ = self.access(request)
        data = s.LastMinuteInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        agenda.set_last_minute(pro, **data.validated_data)
        return Response(s.last_minute_payload(ProProfile.objects.get(pk=pro.pk)))


class BookingQrView(AgendaBase):
    """The QR code of the booking link (to print, to put on the counter)."""

    manage_only = True
    throttle_scope = "printable"

    @extend_schema(tags=["agenda"], responses={(200, "image/png"): OpenApiTypes.BINARY})
    def get(self, request):
        from apps.pros.printables import qr_image

        pro, _ = self.access(request)
        if not pro.slug:
            raise errors.ProNotFound()
        url = f"{settings.SHORT_LINK_BASE_URL.rstrip('/')}/{pro.slug}/rdv"
        buffer = io.BytesIO()
        qr_image(url, 16).save(buffer, format="PNG")
        response = HttpResponse(buffer.getvalue(), content_type="image/png")
        disposition = "attachment" if request.query_params.get("download") == "1" else "inline"
        response["Content-Disposition"] = f'{disposition}; filename="rdv-{pro.slug}.png"'
        response["Cache-Control"] = "private, max-age=300"
        return response


class ClientRecordsView(AgendaBase):
    manage_only = True

    @extend_schema(
        tags=["agenda"],
        parameters=[OpenApiParameter("q", str, required=False)],
        responses=s.ClientRecordSerializer(many=True),
    )
    def get(self, request):
        pro, _ = self.access(request)
        rows = ClientRecord.objects.filter(pro=pro).select_related("client")
        q = (request.query_params.get("q") or "").strip()
        if q:
            rows = rows.filter(Q(name__icontains=q) | Q(phone__icontains=q))
        return Response([s.record_payload(r) for r in rows.order_by("-updated_at")[:100]])


class ClientRecordView(AgendaBase):
    manage_only = True

    def record(self, request, record_id) -> ClientRecord:
        pro, _ = self.access(request)
        found = ClientRecord.objects.filter(pk=record_id, pro=pro).select_related("client").first()
        if found is None:
            raise errors.AppointmentNotFound()
        return found

    def answer(self, found: ClientRecord) -> Response:
        history = (
            agenda.history_of(found)
            .prefetch_related("steps__staff", "options", "recommendations__product")
            .select_related("pro__photo", "pro__country", "payment")[:50]
        )
        return Response(s.record_payload(found, history=history))

    @extend_schema(tags=["agenda"], responses=s.ClientRecordDetailSerializer)
    def get(self, request, record_id):
        return self.answer(self.record(request, record_id))

    @extend_schema(
        tags=["agenda"],
        request=s.ClientRecordInputSerializer,
        responses=s.ClientRecordDetailSerializer,
    )
    def patch(self, request, record_id):
        found = self.record(request, record_id)
        data = s.ClientRecordInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        updated = agenda.update_record(found.pro, found.pk, **data.validated_data)
        return self.answer(updated)


class IcalView(APIView):
    """The agenda for Google Calendar or the iPhone, by its secret address."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "search"

    @extend_schema(
        tags=["agenda"],
        operation_id="agenda_ical",
        parameters=[OpenApiParameter("token", str, OpenApiParameter.PATH)],
        responses={(200, "text/calendar"): OpenApiTypes.STR},
    )
    def get(self, request, token):
        found = BookingSettings.objects.filter(ical_token=token).select_related("pro").first()
        if found is None:
            raise errors.AgendaNotFound()
        response = HttpResponse(agenda.ical(found.pro), content_type="text/calendar; charset=utf-8")
        response["Content-Disposition"] = 'inline; filename="agenda.ics"'
        return response


class DevTimeTravelView(APIView):
    """Development only (never routed in production): an appointment starts in N minutes,
    then the deadlines run (reminders…). Lets the end-to-end tests live a whole day."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(exclude=True)  # development only: never part of the public API
    def post(self, request):
        from django.db.models import F

        from apps.payments.models import Payment

        from .models import AppointmentStep
        from .services import automation

        if not settings.ACCOUNTS_DEV_OTP_ENDPOINT:
            raise errors.AppointmentNotFound()
        found = Appointment.objects.filter(reference=request.data.get("reference", "")).first()
        if found is None:
            raise errors.AppointmentNotFound()
        minutes = int(request.data.get("starts_in_minutes", 60))
        shift = timezone.now() + datetime.timedelta(minutes=minutes) - found.starts_at
        # Earlier test runs may hold that time: they are cancelled first.
        for step in found.steps.exclude(staff__isnull=True):
            for other in Appointment.objects.filter(
                steps__staff_id=step.staff_id,
                steps__blocking=True,
                steps__starts_at__lt=step.ends_at + shift,
                steps__ends_at__gt=step.starts_at + shift,
            ).exclude(pk=found.pk):
                other.status = A.CANCELLED
                other.cancelled_by = Appointment.CancelledBy.SYSTEM
                other.save(update_fields=["status", "cancelled_by", "updated_at"])
                common.set_blocking(other)
        AppointmentStep.objects.filter(appointment=found).update(
            starts_at=F("starts_at") + shift, ends_at=F("ends_at") + shift
        )
        Appointment.objects.filter(pk=found.pk).update(
            starts_at=F("starts_at") + shift, ends_at=F("ends_at") + shift
        )
        if found.payment_id:
            Payment.objects.filter(pk=found.payment_id).update(service_at=found.starts_at + shift)
        common.changed(found.pro)
        return Response(automation.run_all())
