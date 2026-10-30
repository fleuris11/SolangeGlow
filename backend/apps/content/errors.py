from django.utils.translation import gettext_lazy as _

from apps.core.errors import DomainError


class ContactNeeded(DomainError):
    code = "help_contact_needed"
    message = _("Write your name and an e-mail or a phone number so we can answer you.")


class PageNotFound(DomainError):
    code = "page_not_found"
    status_code = 404
    message = _("This page does not exist.")
