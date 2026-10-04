from django.utils.translation import gettext_lazy as _

from apps.core.errors import DomainError


class UnknownPurpose(DomainError):
    code = "unknown_purpose"
    message = _("This file cannot be used here.")


class WrongKind(DomainError):
    code = "wrong_kind"
    message = _(
        "This type of file is not accepted here. Choose a picture, a video or a voice note."
    )


class FileTooLarge(DomainError):
    code = "file_too_large"
    message = _("This file is too large. Choose a file under %(size)s MB.")


class MediaNotFound(DomainError):
    code = "not_found"
    status_code = 404
    message = _("This file does not exist or is not yours.")
