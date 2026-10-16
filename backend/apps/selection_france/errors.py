from django.utils.translation import gettext_lazy as _

from apps.core.errors import DomainError


class SelectionUnavailable(DomainError):
    code = "selection_unavailable"
    status_code = 403
    message = _("The France Selection is not open in your country yet.")


class ProductNotFound(DomainError):
    code = "selection_product_not_found"
    status_code = 404
    message = _("This product does not exist or is no longer offered.")


class OutOfStock(DomainError):
    code = "selection_out_of_stock"
    message = _("This product is out of stock at the merchant for now.")


class AirRestricted(DomainError):
    code = "air_restricted"
    message = _("This kind of product cannot travel by plane: we cannot send it for now.")


class ExpressUnavailable(DomainError):
    code = "express_unavailable"
    message = _("Express shipping is not possible for this product.")


class InvalidChoice(DomainError):
    code = "invalid_choice"
    message = _("Choose one of the offered choices.")


class InvalidQuantity(DomainError):
    code = "selection_invalid_quantity"
    message = _("Choose a quantity between 1 and %(max)s.")


class PickupPointNeeded(DomainError):
    code = "pickup_point_needed"
    message = _("Choose where you will pick up your parcel.")


class CannotBuy(DomainError):
    code = "cannot_buy"
    status_code = 403
    message = _("Purchases are not open to your account.")


class GroupClosed(DomainError):
    code = "group_closed"
    message = _("This group pre-order is closed.")


class OrderNotFound(DomainError):
    code = "selection_order_not_found"
    status_code = 404
    message = _("This order does not exist or is not yours.")


class InvalidStep(DomainError):
    code = "selection_invalid_step"
    status_code = 409
    message = _("This is not possible at this stage of the order.")


class RequestNeedsSomething(DomainError):
    code = "request_needs_something"
    message = _("Paste a link or add a photo of the product.")


class RequestNotFound(DomainError):
    code = "request_not_found"
    status_code = 404
    message = _("This request does not exist or is not yours.")


class QuoteIncomplete(DomainError):
    code = "quote_incomplete"
    message = _("Fill the product, the purchase price, the weight and the category.")


class QuoteExpired(DomainError):
    code = "quote_expired"
    message = _("This quote is no longer valid: send a new request.")


class MixedShipment(DomainError):
    code = "mixed_shipment"
    message = _("Put grouped and express orders in separate shipments.")


class TrackingNeeded(DomainError):
    code = "tracking_needed"
    message = _("Give the carrier and the tracking number before the departure.")
