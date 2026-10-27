from django.utils.translation import gettext_lazy as _

from apps.core.errors import DomainError

# --- Shop and products ---------------------------------------------------------------------------


class ShopUnavailable(DomainError):
    code = "shop_unavailable"
    status_code = 403
    message = _("Shops are not open in this country yet.")


class NotAPro(DomainError):
    code = "not_a_pro"
    status_code = 403
    message = _("Create your showcase first: your shop lives in it.")


class VerificationNeeded(DomainError):
    code = "verification_needed"
    status_code = 403
    message = _("Only a verified pro can sell. Send your identity document in « My showcase ».")


class ProductNotFound(DomainError):
    code = "product_not_found"
    status_code = 404
    message = _("This product does not exist or is no longer on sale.")


class IncompleteProduct(DomainError):
    code = "incomplete_product"
    message = _("Add at least one photo, a price and a category before publishing.")


class TooManyPhotos(DomainError):
    code = "too_many_photos"
    message = _("%(max)s photos at most.")


class InvalidMedia(DomainError):
    code = "invalid_media"
    message = _("This file cannot be used here.")


class InvalidVariants(DomainError):
    code = "invalid_variants"
    message = _(
        "Each choice needs a shade, a size or a colour, and two choices cannot be the same."
    )


class ForbiddenProduct(DomainError):
    code = "forbidden_product"
    message = _("This product cannot be sold on Solange Glow (%(terms)s): %(reasons)s")


class InvalidStep(DomainError):
    code = "invalid_step"
    status_code = 409
    message = _("This is not possible at this stage.")


class InvalidZone(DomainError):
    code = "invalid_zone"
    message = _("Give the zone a name and a fee of 0 or more.")


# --- Promotions ----------------------------------------------------------------------------------


class InvalidPromo(DomainError):
    code = "invalid_promo"
    message = _("Choose a discount in percent or an amount, not both.")


class PromoTooHigh(DomainError):
    code = "promo_too_high"
    message = _("A discount of %(max)s percent at most.")


class CodeTaken(DomainError):
    code = "code_taken"
    status_code = 409
    message = _("You already have a code with this name.")


class InvalidFlashSale(DomainError):
    code = "invalid_flash_sale"
    message = _("The sale ends after it starts, and lasts %(max)s days at most.")


class InvalidBundle(DomainError):
    code = "invalid_bundle"
    message = _("A bundle needs at least two of your products, and a price.")


class PromoNotFound(DomainError):
    code = "promo_not_found"
    message = _("This code does not exist in this shop.")


class PromoOver(DomainError):
    code = "promo_over"
    message = _("This code is not valid at the moment.")


class PromoMinimum(DomainError):
    code = "promo_minimum"
    message = _("This code needs an order of %(minimum)s at least.")


class PromoUsedUp(DomainError):
    code = "promo_used_up"
    message = _("This code was already used.")


# --- Cart and checkout ---------------------------------------------------------------------------


class CannotBuy(DomainError):
    code = "cannot_buy"
    status_code = 403
    message = _("Purchases are not open to your account.")


class OwnShop(DomainError):
    code = "own_shop"
    message = _("You cannot buy in your own shop.")


class Unavailable(DomainError):
    code = "unavailable"
    message = _("« %(title)s » is no longer on sale.")


class OutOfStock(DomainError):
    code = "out_of_stock"
    message = _("« %(title)s »: only %(left)s left.")


class ShopClosed(DomainError):
    code = "shop_closed"
    message = _("%(shop)s is closed for now.")


class InvalidQuantity(DomainError):
    code = "invalid_quantity"
    message = _("Choose a quantity between 1 and %(max)s.")


class CartFull(DomainError):
    code = "cart_full"
    message = _("Your cart is full (%(max)s lines).")


class EmptyCart(DomainError):
    code = "empty_cart"
    message = _("Your cart is empty.")


class DeliveryNotOffered(DomainError):
    code = "delivery_not_offered"
    message = _("%(shop)s does not offer this way of handing over.")


class ZoneNeeded(DomainError):
    code = "zone_needed"
    message = _("Choose your delivery zone.")


class AddressNeeded(DomainError):
    code = "address_needed"
    message = _("Give your address and a phone number for the delivery.")


class OutsideCountry(DomainError):
    code = "outside_country"
    message = _("%(shop)s delivers only in her country. You can pick up your order at her place.")


class MixedCurrencies(DomainError):
    code = "mixed_currencies"
    message = _("Pay the shops of each country separately.")


# --- Orders --------------------------------------------------------------------------------------


class OrderNotFound(DomainError):
    code = "order_not_found"
    status_code = 404
    message = _("This order does not exist or is not yours.")


class ParcelPhotoNeeded(DomainError):
    code = "parcel_photo_needed"
    message = _("Add a photo of the parcel.")


class SaleLivesClosed(DomainError):
    code = "sale_lives_closed"
    status_code = 403
    message = _("Sales lives are not open in your country yet.")


class InvalidSaleLive(DomainError):
    code = "invalid_sale_live"
    message = _("Give a title, a time to come and a length of 15 to %(max)s minutes.")


class SaleLiveNotFound(DomainError):
    code = "sale_live_not_found"
    status_code = 404
    message = _("This live does not exist or cannot change any more.")
