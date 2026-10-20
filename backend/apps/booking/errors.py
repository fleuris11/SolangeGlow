from django.utils.translation import gettext_lazy as _

from apps.core.errors import DomainError


class ProNotFound(DomainError):
    code = "booking_pro_not_found"
    status_code = 404
    message = _("This pro does not take online bookings.")


class ServiceNotFound(DomainError):
    code = "booking_service_not_found"
    status_code = 404
    message = _("This service cannot be booked.")


class StaffNotFound(DomainError):
    code = "staff_not_found"
    status_code = 404
    message = _("This person does not do this service.")


class SlotTaken(DomainError):
    code = "slot_taken"
    status_code = 409
    message = _("This time was just taken. Choose another one.")


class TooSoon(DomainError):
    code = "too_soon"
    message = _("This time is too close: book at least %(minutes)s minutes ahead.")


class TooFar(DomainError):
    code = "too_far"
    message = _("You can book up to %(days)s days ahead.")


class GuestsNotAccepted(DomainError):
    code = "guests_not_accepted"
    status_code = 403
    message = _("Sign in to book with this pro.")


class GuestDetailsNeeded(DomainError):
    code = "guest_details_needed"
    message = _("Give your first name and a phone number.")


class CannotBookYourself(DomainError):
    code = "cannot_book_yourself"
    message = _("You cannot book in your own agenda this way.")


class AppointmentNotFound(DomainError):
    code = "appointment_not_found"
    status_code = 404
    message = _("This appointment does not exist or is not yours.")


class InvalidStep(DomainError):
    code = "booking_invalid_step"
    status_code = 409
    message = _("This is not possible at this stage of the appointment.")


class NotYet(DomainError):
    code = "not_yet"
    message = _("The appointment has not started yet.")


class NotLateEnough(DomainError):
    code = "not_late_enough"
    message = _("Wait %(minutes)s minutes after the start before marking an absence.")


class InvalidHours(DomainError):
    code = "invalid_hours"
    message = _("The end must come after the start.")


class InvalidStaff(DomainError):
    code = "invalid_staff"
    message = _("Give a name and choose a colour like #C8102E.")


class AlreadyInList(DomainError):
    code = "already_in_list"
    status_code = 409
    message = _("You are already on the waiting list for this day.")


class OfferExpired(DomainError):
    code = "offer_expired"
    status_code = 409
    message = _("This place was offered to someone else after the waiting time.")


class InvalidGroup(DomainError):
    code = "invalid_group"
    message = _("A group is 2 to %(max)s people.")


class GroupDoesNotFit(DomainError):
    code = "group_does_not_fit"
    status_code = 409
    message = _("Not enough room at this time for the whole group.")


class ProductNotFound(DomainError):
    code = "booking_product_not_found"
    status_code = 404
    message = _("This product is not on sale in your shop.")


class DepositNeedsAccount(DomainError):
    code = "deposit_needs_account"
    status_code = 403
    message = _("This service asks for a deposit: sign in to pay it.")


class AgendaNotFound(DomainError):
    code = "agenda_not_found"
    status_code = 404
    message = _("You have no agenda yet.")


class ManagersOnly(DomainError):
    code = "agenda_managers_only"
    status_code = 403
    message = _("Only the owner of the salon can change this.")


class GroupNotFound(DomainError):
    code = "group_not_found"
    status_code = 404
    message = _("This group booking does not exist any more.")


class SignInToPay(DomainError):
    code = "sign_in_to_pay"
    status_code = 403
    message = _("Sign in to pay the deposit.")


class GiftCardRefused(DomainError):
    code = "gift_card_refused"
    message = _("This gift card cannot pay the deposit: check the code and its balance.")
