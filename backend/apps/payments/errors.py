from django.utils.translation import gettext_lazy as _

from apps.core.errors import DomainError


class PaymentNotFound(DomainError):
    code = "payment_not_found"
    status_code = 404
    message = _("This payment does not exist or is not yours.")


class InvalidTransition(DomainError):
    code = "invalid_transition"
    status_code = 409
    message = _("This is not possible at this stage of the payment.")


class CancelNotAllowed(DomainError):
    code = "cancel_not_allowed"
    status_code = 409
    message = _("The seller is already preparing this order: write to her to cancel it.")


class InvalidPayment(DomainError):
    code = "invalid_payment"
    message = _("The amounts of this payment are not valid.")


class PaymentsUnavailable(DomainError):
    code = "payments_unavailable"
    status_code = 503
    message = _("Payments are not available in this country yet.")


class WrongCode(DomainError):
    code = "wrong_code"
    message = _("This code is not right. Attempts left: %(left)s.")


class CodeLocked(DomainError):
    code = "code_locked"
    status_code = 423
    message = _("Too many wrong codes. The client can ask for a new code in her app.")


class TooManyNewCodes(DomainError):
    code = "too_many_new_codes"
    message = _("No more new code possible: contact the support.")


class InvalidCourierLink(DomainError):
    code = "invalid_courier_link"
    status_code = 404
    message = _("This delivery link is not valid any more. Ask the seller for a new one.")


class ProofNeeded(DomainError):
    code = "proof_needed"
    message = _("Add a picture as proof of delivery.")


class DisputeNotAllowed(DomainError):
    code = "dispute_not_allowed"
    status_code = 409
    message = _("A dispute can be opened once the order is paid and before it is closed.")


class AlreadyDecided(DomainError):
    code = "already_decided"
    status_code = 409
    message = _("This dispute was already decided.")


class InvalidRefundAmount(DomainError):
    code = "invalid_refund_amount"
    message = _("Choose an amount above 0 and below the total paid (%(total)s).")


class BelowMinimum(DomainError):
    code = "below_minimum"
    message = _("The minimum payout is %(minimum)s.")


class NotEnoughMoney(DomainError):
    code = "not_enough_money"
    message = _("This is more than your available balance (%(available)s).")


class NoPayoutMethod(DomainError):
    code = "no_payout_method"
    message = _("Add where you want to receive your money first.")


class IdentityNeeded(DomainError):
    code = "identity_needed"
    status_code = 403
    message = _("Your identity must be checked before you can receive money.")


class InvalidMedia(DomainError):
    code = "invalid_media"
    message = _("This file cannot be used here.")
