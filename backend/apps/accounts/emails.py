"""The e-mails of the account itself: confirm the address, choose a new password, « you already
have an account ». Plain text in the person's language (texts editable as translations)."""

from __future__ import annotations

from dataclasses import dataclass

from django.utils import translation
from django.utils.translation import gettext as _


@dataclass(frozen=True)
class AccountEmail:
    subject: str
    body: str


def build(kind: str, *, link: str, first_name: str, hours: int, language: str) -> AccountEmail:
    with translation.override(language):
        hello = _("Hello %(name)s,") % {"name": first_name} if first_name else _("Hello,")
        if kind == "confirm":
            subject = _("Confirm your e-mail address")
            lines = [
                _("Welcome to Solange Glow! One click to confirm your address:"),
                link,
                _("This link works for %(hours)s hours.") % {"hours": hours},
            ]
        elif kind == "reset":
            subject = _("Choose a new password")
            lines = [
                _("To choose a new password, open this link:"),
                link,
                _("This link works for %(hours)s hours and only once.") % {"hours": hours},
            ]
        else:  # "exists": someone signed up again with an address that has an account
            subject = _("You already have a Solange Glow account")
            lines = [
                _("Someone tried to create an account with this address: you already have one."),
                _("To sign in, choose a new password with this link:"),
                link,
                _("This link works for %(hours)s hours and only once.") % {"hours": hours},
            ]
        footer = _("If you did not ask for this, ignore this e-mail: nothing changes.")
        signature = _("The Solange Glow team")
        body = "\n\n".join([hello, *lines, footer, signature]) + "\n"
        return AccountEmail(subject=subject, body=body)
