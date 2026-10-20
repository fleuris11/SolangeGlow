from django.conf import settings
from django.urls import path

from . import views

MINE = "booking/appointments/<uuid:appointment_id>"
GUEST = "booking/manage/<str:token>"
AG = "me/agenda/appointments/<uuid:appointment_id>"

urlpatterns = [
    # Public: the booking page of a pro.
    path("pros/<slug:slug>/booking", views.BookingPageView.as_view(), name="booking-page"),
    path("pros/<slug:slug>/booking/slots", views.SlotsView.as_view(), name="booking-slots"),
    path(
        "pros/<slug:slug>/booking/waitlist",
        views.WaitlistJoinView.as_view(),
        name="booking-waitlist-join",
    ),
    path(
        "pros/<slug:slug>/booking/groups", views.GroupCreateView.as_view(), name="booking-group-new"
    ),
    path("booking/groups/<str:token>", views.GroupView.as_view(), name="booking-group"),
    path(
        "booking/groups/<str:token>/share",
        views.GroupShareView.as_view(),
        name="booking-group-share",
    ),
    # The client (signed in) and the guest (her secret link).
    path("booking/appointments", views.ClientAppointmentsView.as_view(), name="my-appointments"),
    path(MINE, views.ClientAppointmentView.as_view(), name="my-appointment"),
    path(f"{MINE}/cancel", views.ClientCancelView.as_view(), name="my-appointment-cancel"),
    path(f"{MINE}/answer", views.ClientAnswerView.as_view(), name="my-appointment-answer"),
    path(f"{MINE}/accept", views.ClientAcceptOfferView.as_view(), name="my-appointment-accept"),
    path(f"{MINE}/pay", views.ClientPayView.as_view(), name="my-appointment-pay"),
    path(GUEST, views.ClientAppointmentView.as_view(), name="guest-appointment"),
    path(f"{GUEST}/cancel", views.ClientCancelView.as_view(), name="guest-appointment-cancel"),
    path(f"{GUEST}/answer", views.ClientAnswerView.as_view(), name="guest-appointment-answer"),
    path(f"{GUEST}/accept", views.ClientAcceptOfferView.as_view(), name="guest-appointment-accept"),
    path("booking/waitlist", views.ClientWaitlistView.as_view(), name="my-waitlist"),
    path(
        "booking/waitlist/<uuid:entry_id>",
        views.ClientWaitlistEntryView.as_view(),
        name="my-waitlist-entry",
    ),
    # The agenda of the pro and her collaborators.
    path("me/agenda", views.AgendaView.as_view(), name="agenda"),
    path("me/agenda/appointments", views.AgendaAppointmentsView.as_view(), name="agenda-new"),
    path(AG, views.AgendaAppointmentView.as_view(), name="agenda-appointment"),
    path(f"{AG}/confirm", views.AgendaConfirmView.as_view(), name="agenda-confirm"),
    path(f"{AG}/decline", views.AgendaDeclineView.as_view(), name="agenda-decline"),
    path(f"{AG}/propose", views.AgendaProposeView.as_view(), name="agenda-propose"),
    path(f"{AG}/move", views.AgendaMoveView.as_view(), name="agenda-move"),
    path(f"{AG}/complete", views.AgendaCompleteView.as_view(), name="agenda-complete"),
    path(f"{AG}/no-show", views.AgendaNoShowView.as_view(), name="agenda-no-show"),
    path(f"{AG}/cancel", views.AgendaCancelView.as_view(), name="agenda-cancel"),
    path(f"{AG}/photos", views.AgendaPhotoView.as_view(), name="agenda-photo"),
    path(f"{AG}/advice", views.AgendaAdviceView.as_view(), name="agenda-advice"),
    path("me/agenda/time-off", views.TimeOffView.as_view(), name="agenda-time-off"),
    path(
        "me/agenda/time-off/<uuid:time_off_id>",
        views.TimeOffItemView.as_view(),
        name="agenda-time-off-item",
    ),
    path("me/agenda/staff", views.StaffListView.as_view(), name="agenda-staff"),
    path(
        "me/agenda/staff/<uuid:staff_id>", views.StaffItemView.as_view(), name="agenda-staff-item"
    ),
    path(
        "me/agenda/staff/<uuid:staff_id>/hours",
        views.StaffHoursView.as_view(),
        name="agenda-staff-hours",
    ),
    path("me/agenda/resources", views.ResourcesView.as_view(), name="agenda-resources"),
    path(
        "me/agenda/resources/<uuid:resource_id>",
        views.ResourceItemView.as_view(),
        name="agenda-resource",
    ),
    path("me/agenda/settings", views.AgendaSettingsView.as_view(), name="agenda-settings"),
    path("me/agenda/last-minute", views.LastMinuteView.as_view(), name="agenda-last-minute"),
    path("me/agenda/qr.png", views.BookingQrView.as_view(), name="agenda-qr"),
    path("me/agenda/clients", views.ClientRecordsView.as_view(), name="agenda-clients"),
    path(
        "me/agenda/clients/<uuid:record_id>",
        views.ClientRecordView.as_view(),
        name="agenda-client",
    ),
    path("agenda/<str:token>.ics", views.IcalView.as_view(), name="agenda-ical"),
]

if settings.ACCOUNTS_DEV_OTP_ENDPOINT:
    urlpatterns.append(
        path("dev/booking/time-travel", views.DevTimeTravelView.as_view(), name="dev-time-travel")
    )
