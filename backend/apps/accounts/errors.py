from django.utils.translation import gettext_lazy as _

from apps.core.errors import DomainError


class InvalidDestination(DomainError):
    code = "invalid_destination"
    message = _("This number or e-mail address is not valid. Check it and try again.")


class TooManyRequests(DomainError):
    code = "too_many_requests"
    status_code = 429
    message = _("You asked for many codes. Wait a little, then try again.")


class ResendTooSoon(DomainError):
    code = "resend_too_soon"
    status_code = 429
    message = _("A code was just sent. Wait a few seconds before asking for a new one.")


class DeliveryFailed(DomainError):
    code = "delivery_failed"
    status_code = 503
    message = _("We could not send the code. Check the number, then try again in a minute.")


class InvalidCode(DomainError):
    code = "invalid_code"
    message = _("The code does not match. Check the 6 digits you received.")


class CodeExpired(DomainError):
    code = "code_expired"
    message = _("This code has expired. Ask for a new code.")


class TooManyAttempts(DomainError):
    code = "too_many_attempts"
    status_code = 429
    message = _("Too many wrong codes. Ask for a new code.")


class ChallengeNotFound(DomainError):
    code = "challenge_not_found"
    status_code = 404
    message = _("This code is no longer valid. Ask for a new code.")


class AccountSuspended(DomainError):
    code = "account_suspended"
    status_code = 403
    message = _("This account is suspended. Write to our team to find out why.")


class InvalidCredentials(DomainError):
    code = "invalid_credentials"
    status_code = 401
    message = _("The number, e-mail or password is not correct. You can also sign in with a code.")


class InvalidImage(DomainError):
    code = "invalid_image"
    message = _("This file is not a photo we can use. Choose a JPEG, PNG or WebP photo.")


class ImageTooLarge(DomainError):
    code = "image_too_large"
    message = _("This photo is too large. Choose a photo under %(size)s MB.")
