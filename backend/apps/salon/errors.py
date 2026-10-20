from django.utils.translation import gettext_lazy as _

from apps.core.errors import DomainError


class NotFound(DomainError):
    code = "salon_not_found"
    status_code = 404
    message = _("This does not exist or is not in your salon.")


class InvalidPackage(DomainError):
    code = "invalid_package"
    message = _("Give a name, 2 to 50 sessions, a price and a service of your list.")


class PackageUsedUp(DomainError):
    code = "package_used_up"
    message = _("No session left on this package.")


class InvalidInstallments(DomainError):
    code = "invalid_installments"
    message = _("Split in 2 to %(max)s payments, with dates after today.")


class InstallmentPaid(DomainError):
    code = "installment_paid"
    message = _("This payment was already made.")


class InvalidGiftCard(DomainError):
    code = "invalid_gift_card"
    message = _("Choose an amount between %(min)s and %(max)s.")


class GiftCardNotFound(DomainError):
    code = "gift_card_not_found"
    status_code = 404
    message = _("No usable gift card with this code in this salon.")


class NotEnoughBalance(DomainError):
    code = "not_enough_balance"
    message = _("The gift card only has %(balance)s left.")


class InvalidStockItem(DomainError):
    code = "invalid_stock_item"
    message = _("Give a name and a barcode of 8 to 14 digits (or none).")


class BarcodeTaken(DomainError):
    code = "barcode_taken"
    message = _("Another product of your stock has this barcode.")


class InvalidMovement(DomainError):
    code = "invalid_movement"
    message = _("Give a quantity (not zero).")


class InvalidPayment(DomainError):
    code = "invalid_on_site_payment"
    message = _("Give an amount and how it was paid.")


class MethodNotAvailable(DomainError):
    code = "payment_method_not_available"
    message = _("This way of paying cannot be recorded in your country.")


class TerminalNotConfigured(DomainError):
    code = "terminal_not_configured"
    message = _("Card payment on the phone is not available yet.")


class AlreadyCancelled(DomainError):
    code = "already_cancelled"
    message = _("This was already cancelled.")


class InvalidCampaign(DomainError):
    code = "invalid_campaign"
    message = _("Give a name and a message (and a subject for an e-mail).")


class CampaignLimit(DomainError):
    code = "campaign_limit"
    message = _("You can send %(limit)s campaigns a month.")


class CampaignSent(DomainError):
    code = "campaign_sent"
    message = _("This campaign was already sent.")


class InvalidUnsubscribe(DomainError):
    code = "invalid_unsubscribe"
    status_code = 404
    message = _("This link does not work any more.")
