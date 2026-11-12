from django.utils.translation import gettext_lazy as _

from apps.core.errors import DomainError


class ProspectEmailNeeded(DomainError):
    code = "prospect_email_needed"
    message = _("This prospect has no e-mail address: add it first.")


class ProspectAccountExists(DomainError):
    code = "prospect_account_exists"
    message = _(
        "An account already uses this e-mail address: this person is already on Solange Glow."
    )


class ShowcaseNeeded(DomainError):
    code = "showcase_needed"
    message = _("Prepare the showcase of this prospect first: this e-mail presents it.")


class ProspectDeclined(DomainError):
    code = "prospect_declined"
    message = _("This prospect asked not to be contacted any more.")


class DailyEmailLimit(DomainError):
    code = "daily_email_limit"
    status_code = 429
    message = _("%(max)s e-mails to prospects were already sent today. Continue tomorrow.")


class TemplateNotFound(DomainError):
    code = "template_not_found"
    status_code = 404
    message = _("This standard e-mail does not exist or is switched off.")


class ShowcaseNotOnline(DomainError):
    code = "showcase_not_online"
    message = _("Publish the showcase first: this message gives its address.")


class ShowcaseNotPrepared(DomainError):
    code = "showcase_not_prepared"
    message = _("Prepare the showcase of this prospect first.")
