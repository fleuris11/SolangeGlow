from django.utils.translation import gettext_lazy as _

from apps.core.errors import DomainError


class NotAPro(DomainError):
    code = "not_a_pro"
    status_code = 404
    message = _("You do not have a showcase yet. Start with « Become a pro ».")


class ProNotFound(DomainError):
    code = "pro_not_found"
    status_code = 404
    message = _("This pro does not exist or is not visible any more.")


class SlugInvalid(DomainError):
    code = "slug_invalid"
    message = _("Use 3 to 40 lowercase letters, digits or dashes, e.g. aicha-tresses.")


class SlugTaken(DomainError):
    code = "slug_taken"
    message = _("This link is already used. Try another one, e.g. with your district.")


class InvalidSocialLink(DomainError):
    code = "invalid_social_link"
    message = _("This link is not valid. Paste the address of your page or your @name.")


class InvalidLocation(DomainError):
    code = "invalid_location"
    message = _("This position is not valid. Place the point on the map again.")


class InvalidArea(DomainError):
    code = "invalid_area"
    message = _("This area is not valid. Draw it again with at least 3 points.")


class RadiusTooLarge(DomainError):
    code = "radius_too_large"
    message = _("The travel radius cannot be more than %(km)s km.")


class InvalidPrice(DomainError):
    code = "invalid_price"
    message = _("Give a price, or choose « On quote ».")


class NameRequired(DomainError):
    code = "name_required"
    message = _("Give a name to this service.")


class InvalidDuration(DomainError):
    code = "invalid_duration"
    message = _("Give the time of the service, in minutes.")


class TooMany(DomainError):
    code = "too_many"
    message = _("You reached the limit of %(limit)s. Remove one before adding another.")


class InvalidHours(DomainError):
    code = "invalid_hours"
    message = _("The hours of %(day)s overlap or close before they open. Check them.")


class InvalidClosure(DomainError):
    code = "invalid_closure"
    message = _("The last day of the closure must be after the first one.")


class NotReadyToPublish(DomainError):
    code = "not_ready"
    message = _("Your showcase is not complete yet. Fill in what is missing.")


class Suspended(DomainError):
    code = "suspended"
    status_code = 403
    message = _("Your showcase is suspended. Write to the support team to know why.")


class MediaNotReady(DomainError):
    code = "media_not_ready"
    message = _("This file is not ready or was refused. Send it again.")


class VerificationAlreadySent(DomainError):
    code = "verification_pending"
    message = _("Your documents are being checked. You will get an answer soon.")


class AlreadyVerified(DomainError):
    code = "already_verified"
    message = _("You are already a verified pro.")


class ArrivalTooSoon(DomainError):
    code = "arrival_too_soon"
    status_code = 429
    message = _("The pro was just told you are here. Wait a few minutes.")


class ArrivalNotPossible(DomainError):
    code = "arrival_not_possible"
    message = _("This pro does not receive clients at a place. Write to her instead.")


class IdentityRequired(DomainError):
    code = "identity_required"
    status_code = 401
    message = _("Sign in, or give your first name and number, to tell the pro you are here.")
