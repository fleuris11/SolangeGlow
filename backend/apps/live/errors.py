from django.utils.translation import gettext_lazy as _

from apps.core.errors import DomainError


class LiveNotFound(DomainError):
    code = "live_not_found"
    status_code = 404
    message = _("This live does not exist or is not open to you.")


class NotHost(DomainError):
    code = "not_host"
    status_code = 403
    message = _("Only the host of this live can do this.")


class NotOnAir(DomainError):
    code = "not_on_air"
    message = _("This live is not on air.")


class TooEarly(DomainError):
    code = "live_too_early"
    message = _("You can go on air %(minutes)s minutes before the planned time.")


class LiveOver(DomainError):
    code = "live_over"
    message = _("This live is over.")


class LiveFull(DomainError):
    code = "live_room_full"
    status_code = 409
    message = _("The live is full (%(max)s people). Try again in a moment.")


class SignInToAsk(DomainError):
    code = "sign_in_to_ask"
    status_code = 403
    message = _("Sign in to write a question.")


class CannotAsk(DomainError):
    code = "cannot_ask"
    status_code = 403
    message = _("You cannot write in this live.")


class EmptyQuestion(DomainError):
    code = "empty_question"
    message = _("Write your question (300 characters at most).")


class HandsClosed(DomainError):
    code = "hands_closed"
    message = _("Raising your hand is not possible in this live.")


class NoHand(DomainError):
    code = "no_hand"
    status_code = 404
    message = _("This person has not raised her hand.")


class MonthlyLimit(DomainError):
    code = "live_monthly_limit"
    status_code = 403
    message = _("You have used your %(max)s lives of the month. Glow Pro Premium gives you more.")


class VideoUnavailable(DomainError):
    code = "video_unavailable"
    status_code = 503
    message = _("The live video is not available right now. Try again in a few minutes.")
