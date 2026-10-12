from django.utils.translation import gettext_lazy as _

from apps.core.errors import DomainError


class CannotReportYourself(DomainError):
    code = "cannot_report_yourself"
    message = _("You cannot report your own content.")


class AlreadyReported(DomainError):
    code = "already_reported"
    message = _("You already reported this. Our team is looking at it.")


class CannotBlockYourself(DomainError):
    code = "cannot_block_yourself"
    message = _("You cannot block yourself.")


class UnknownTarget(DomainError):
    code = "unknown_target"
    status_code = 404
    message = _("This content does not exist any more.")


class Restricted(DomainError):
    code = "restricted"
    status_code = 403
    message = _("You cannot post or comment for now, after a decision of the moderation team.")
