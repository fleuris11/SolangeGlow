from django.utils.translation import gettext_lazy as _

from apps.core.errors import DomainError


class PremiumRequired(DomainError):
    code = "premium_required"
    status_code = 403
    message = _("This is part of Glow Pro Premium. Try it for free in « My plan ».")


class StaffLimit(DomainError):
    code = "staff_limit"
    status_code = 403
    message = _("The free plan has %(limit)s people besides you. Go Premium to add more.")


class TrialUsed(DomainError):
    code = "trial_used"
    message = _("You already had your free trial.")


class AlreadyPremium(DomainError):
    code = "already_premium"
    message = _("You are already on this plan.")


class PlanNotFound(DomainError):
    code = "plan_not_found"
    status_code = 404
    message = _("This plan is not offered in your country.")


class NoPayment(DomainError):
    code = "nothing_to_pay"
    message = _("There is nothing to pay right now.")


class InvalidWidget(DomainError):
    code = "invalid_widget"
    message = _("Give a colour like #C8102E and website addresses like salon.fr.")


class NotAllowedHere(DomainError):
    code = "widget_not_allowed"
    status_code = 403
    message = _("This booking module is not allowed on this website.")


class NotAPro(DomainError):
    code = "glowpro_not_a_pro"
    status_code = 404
    message = _("Create your pro showcase first.")
