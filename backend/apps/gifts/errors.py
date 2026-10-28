from django.utils.translation import gettext_lazy as _

from apps.core.errors import DomainError


class GiftNotFound(DomainError):
    code = "gift_not_found"
    status_code = 404
    message = _("This gift does not exist or can no longer be used.")


class GiftsUnavailable(DomainError):
    code = "gifts_unavailable"
    message = _("Gifts cannot be sent from here yet.")


class CannotOffer(DomainError):
    code = "cannot_offer"
    status_code = 403
    message = _("You must be an adult to offer a gift.")


class NothingToOffer(DomainError):
    code = "nothing_to_offer"
    message = _("This cannot be offered right now. Choose something else.")


class OfferYourself(DomainError):
    code = "offer_yourself"
    message = _("You cannot offer your own service or product.")


class InvalidAmount(DomainError):
    code = "gift_invalid_amount"
    message = _("Choose an amount between %(min)s and %(max)s.")


class RecipientNeeded(DomainError):
    code = "gift_recipient_needed"
    message = _("Write the first name and a phone number in Benin.")


class InvalidSendDate(DomainError):
    code = "gift_invalid_send_date"
    message = _("Choose a sending date within %(days)s days.")


class NotOpenYet(DomainError):
    code = "gift_not_open_yet"
    message = _("This gift opens on %(date)s. A little patience!")


class WrongKind(DomainError):
    code = "gift_wrong_kind"
    message = _("This gift cannot be used this way.")


class AlreadyUsed(DomainError):
    code = "gift_already_used"
    message = _("This gift was already used.")


class NotEnoughLeft(DomainError):
    code = "gift_not_enough"
    message = _("The card has %(balance)s left: it must pay the whole purchase.")


class CardOnlyHere(DomainError):
    code = "gift_card_only_here"
    message = _("A Glow gift card pays purchases in FCFA, in Benin.")


class CannotCancel(DomainError):
    code = "gift_cannot_cancel"
    message = _("This gift can no longer be cancelled: it was used or the time is over.")


class GiverCannotDoThis(DomainError):
    code = "gift_giver"
    status_code = 403
    message = _("Only the person who receives the gift can do this.")


class PhotoNotFound(DomainError):
    code = "gift_photo_not_found"
    status_code = 404
    message = _("This photo does not exist.")
