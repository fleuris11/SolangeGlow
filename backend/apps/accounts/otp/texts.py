from django.utils import translation
from django.utils.translation import gettext as _

from .base import OtpMessage


def code_text(message: OtpMessage) -> str:
    """Short text for SMS and e-mail, in the language of the person."""
    with translation.override(message.locale):
        return _(
            "Solange Glow: your code is %(code)s. It expires in %(minutes)s minutes. "
            "Never share it."
        ) % {"code": message.code, "minutes": message.ttl_minutes}


def email_subject(message: OtpMessage) -> str:
    with translation.override(message.locale):
        return _("Your Solange Glow code: %(code)s") % {"code": message.code}
