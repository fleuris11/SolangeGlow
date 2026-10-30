from django.utils.translation import gettext_lazy as _

from apps.core.errors import DomainError


class AdNotFound(DomainError):
    code = "ad_not_found"
    status_code = 404
    message = _("This ad does not exist any more.")


class UnknownPlacement(DomainError):
    code = "ad_unknown_placement"
    message = _("This place does not show ads.")


class BoostsUnavailable(DomainError):
    code = "boosts_unavailable"
    message = _("Boosts are not open in your country yet.")


class NotAPro(DomainError):
    code = "boost_not_a_pro"
    status_code = 403
    message = _("Only a published pro can boost her showcase.")


class NoBoostPrice(DomainError):
    code = "boost_no_price"
    message = _("No price is set for a boost in your country yet.")


class BoostRunning(DomainError):
    code = "boost_running"
    message = _("A boost is already running until %(until)s.")


class InvalidCampaign(DomainError):
    code = "ad_invalid_campaign"
    message = _("Check the dates and add at least one active creative with a placement.")
