"""What the web app gets from the shop, and what it sends."""

from __future__ import annotations

from django.utils import timezone
from rest_framework import serializers

from apps.core.media.api import MediaSerializer
from apps.core.media.services import asset_payload
from apps.live.serializers import LiveQuotaSerializer
from apps.messaging.payloads import person_payload
from apps.messaging.serializers import PersonSerializer
from apps.payments.serializers import PaymentSerializer, payment_payload

from . import prices
from .models import (
    ZONE_MODES,
    DeliveryMode,
    DeliveryZone,
    Order,
    Product,
    PromoCode,
    SaleLive,
    Variant,
)


def _iso(value):
    return value.isoformat() if value else None


def _ready(asset):
    return asset_payload(asset) if asset is not None else None


# --- Catalogue -----------------------------------------------------------------------------------


def category_payload(category) -> dict | None:
    if category is None:
        return None
    return {"key": category.key, "name": category.name, "icon": category.icon}


class ProductCategorySerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()
    icon = serializers.CharField(allow_blank=True)


def variant_payload(variant: Variant, sale) -> dict:
    return {
        "id": str(variant.pk),
        "shade": variant.shade,
        "swatch": variant.swatch,
        "size": variant.size,
        "color": variant.color,
        "label": variant.label,
        "price_minor": prices.unit_price(variant, sale),
        "before_minor": variant.base_price_minor if sale else None,
        "own_price_minor": variant.price_minor,
        "stock": variant.stock,
        "is_active": variant.is_active,
    }


class VariantSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    shade = serializers.CharField(allow_blank=True)
    swatch = serializers.CharField(allow_blank=True)
    size = serializers.CharField(allow_blank=True)
    color = serializers.CharField(allow_blank=True)
    label = serializers.CharField(allow_blank=True)
    price_minor = serializers.IntegerField()
    before_minor = serializers.IntegerField(allow_null=True)
    own_price_minor = serializers.IntegerField(allow_null=True)
    stock = serializers.IntegerField()
    is_active = serializers.BooleanField()


def flash_payload(sale) -> dict | None:
    if sale is None:
        return None
    left = sale.quantity_limit - sale.sold_count if sale.quantity_limit is not None else None
    return {
        "id": str(sale.pk),
        "percent_off": sale.percent_off,
        "starts_at": _iso(sale.starts_at),
        "ends_at": _iso(sale.ends_at),
        "left": left,
    }


class FlashSaleSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    percent_off = serializers.IntegerField()
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    left = serializers.IntegerField(allow_null=True)


def shop_brief(pro) -> dict:
    return {
        "slug": pro.slug,
        "name": pro.display_name,
        "photo": _ready(pro.photo),
        "city": pro.city,
        "is_verified": pro.is_verified,
        "rating_average": float(pro.rating_average) if pro.rating_average is not None else None,
        "rating_count": pro.rating_count,
    }


class ShopBriefSerializer(serializers.Serializer):
    slug = serializers.CharField(allow_null=True)
    name = serializers.CharField()
    photo = MediaSerializer(allow_null=True)
    city = serializers.CharField(allow_blank=True)
    is_verified = serializers.BooleanField()
    rating_average = serializers.FloatField(allow_null=True)
    rating_count = serializers.IntegerField()


def product_summary(product: Product, *, wished: frozenset = frozenset()) -> dict:
    sale = prices.active_flash_sale(product)
    price, before = prices.lowest_price(product)
    photo = next(iter(product.photos.all()), None)
    return {
        "id": str(product.pk),
        "slug": product.slug,
        "title": product.title,
        "category": category_payload(product.category),
        "currency": product.currency,
        "price_minor": price,
        "before_minor": before if sale else None,
        "photo": _ready(photo.media) if photo else None,
        "in_stock": prices.in_stock(product),
        "flash_sale": flash_payload(sale),
        "sold_count": product.sold_count,
        "wished": product.pk in wished,
        "shop_slug": product.pro.slug,
    }


class ProductSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    slug = serializers.CharField()
    title = serializers.CharField()
    category = ProductCategorySerializer(allow_null=True)
    currency = serializers.CharField()
    price_minor = serializers.IntegerField()
    before_minor = serializers.IntegerField(allow_null=True)
    photo = MediaSerializer(allow_null=True)
    in_stock = serializers.BooleanField()
    flash_sale = FlashSaleSerializer(allow_null=True)
    sold_count = serializers.IntegerField()
    wished = serializers.BooleanField()
    shop_slug = serializers.CharField(allow_null=True)


def delivery_payload(shop) -> dict:
    zones = [z for z in shop.zones.all() if z.is_active]
    return {
        "is_open": shop.is_open,
        "pickup": shop.pickup,
        "pickup_note": shop.pickup_note,
        "seller_delivery": shop.seller_delivery,
        "partner_delivery": shop.partner_delivery,
        "partner_name": shop.partner_name,
        "return_policy": shop.return_policy,
        "zones": [zone_payload(z) for z in zones],
    }


def zone_payload(zone: DeliveryZone) -> dict:
    return {"id": str(zone.pk), "mode": zone.mode, "name": zone.name, "fee_minor": zone.fee_minor}


class ZoneSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    mode = serializers.ChoiceField(choices=ZONE_MODES)
    name = serializers.CharField()
    fee_minor = serializers.IntegerField()


class DeliverySerializer(serializers.Serializer):
    is_open = serializers.BooleanField()
    pickup = serializers.BooleanField()
    pickup_note = serializers.CharField(allow_blank=True)
    seller_delivery = serializers.BooleanField()
    partner_delivery = serializers.BooleanField()
    partner_name = serializers.CharField(allow_blank=True)
    return_policy = serializers.CharField(allow_blank=True)
    zones = ZoneSerializer(many=True)


def bundle_payload(bundle) -> dict:
    return {
        "id": str(bundle.pk),
        "title": bundle.title,
        "description": bundle.description,
        "photo": _ready(bundle.photo),
        "currency": bundle.currency,
        "price_minor": bundle.price_minor,
        "worth_minor": prices.bundle_worth(bundle),
        "stock": prices.bundle_stock(bundle),
        "is_active": bundle.is_active,
        "items": [
            {
                "variant_id": str(item.variant_id),
                "product_id": str(item.variant.product_id),
                "title": item.variant.product.title,
                "label": item.variant.label,
                "quantity": item.quantity,
            }
            for item in bundle.items.all()
        ],
    }


class BundleItemSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    product_id = serializers.UUIDField()
    title = serializers.CharField()
    label = serializers.CharField(allow_blank=True)
    quantity = serializers.IntegerField()


class BundleSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    photo = MediaSerializer(allow_null=True)
    currency = serializers.CharField()
    price_minor = serializers.IntegerField()
    worth_minor = serializers.IntegerField()
    stock = serializers.IntegerField()
    is_active = serializers.BooleanField()
    items = BundleItemSerializer(many=True)


class ShopLiveSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    starts_at = serializers.DateTimeField()
    status = serializers.ChoiceField(choices=SaleLive.Status.choices)
    replay = serializers.BooleanField(help_text="A replay can be watched.")
    link = serializers.CharField()
    time_zone = serializers.CharField()


class ShopPageSerializer(serializers.Serializer):
    shop = ShopBriefSerializer()
    delivery = DeliverySerializer()
    categories = ProductCategorySerializer(many=True)
    products = ProductSummarySerializer(many=True)
    bundles = BundleSerializer(many=True)
    lives = ShopLiveSerializer(many=True, help_text="Sales lives: on air, coming, replays.")


def product_detail(product: Product, viewer=None, *, wished: bool = False, watching=()):
    from .services.alerts import product_link

    sale = prices.active_flash_sale(product)
    upcoming = prices.next_flash_sale(product)
    shop = getattr(product.pro, "shop", None)
    signed_in = viewer is not None and viewer.is_authenticated
    return {
        **product_summary(product, wished=frozenset([product.pk]) if wished else frozenset()),
        "description": product.description,
        "description_voice": _ready(product.description_voice),
        "video": _ready(product.video),
        "photos": [asset_payload(p.media) for p in product.photos.all()],
        "variants": [variant_payload(v, sale) for v in prices.sellable_variants(product)],
        "prep_days": product.prep_days,
        "next_flash_sale": flash_payload(upcoming),
        "shop": shop_brief(product.pro),
        "delivery": delivery_payload(shop) if shop else None,
        "watching": [str(v) for v in watching],
        "is_mine": signed_in and product.pro.user_id == viewer.pk,
        "link": product_link(product),
    }


class ProductDetailSerializer(ProductSummarySerializer):
    description = serializers.CharField(allow_blank=True)
    description_voice = MediaSerializer(allow_null=True)
    video = MediaSerializer(allow_null=True)
    photos = MediaSerializer(many=True)
    variants = VariantSerializer(many=True)
    prep_days = serializers.IntegerField()
    next_flash_sale = FlashSaleSerializer(allow_null=True)
    shop = ShopBriefSerializer()
    delivery = DeliverySerializer(allow_null=True)
    watching = serializers.ListField(child=serializers.UUIDField())
    is_mine = serializers.BooleanField()
    link = serializers.CharField()


# --- The pro's own products ----------------------------------------------------------------------


def my_product_payload(product: Product) -> dict:
    sale = prices.active_flash_sale(product)
    return {
        **product_summary(product),
        "status": product.status,
        "visibility": product.visibility,
        "review_reason": product.review_reason,
        "matched_terms": product.matched_terms,
        "description": product.description,
        "description_voice": _ready(product.description_voice),
        "video": _ready(product.video),
        "photos": [asset_payload(p.media) for p in product.photos.all()],
        "base_price_minor": product.price_minor,
        "prep_days": product.prep_days,
        "variants": [variant_payload(v, sale) for v in product.variants.all() if v.is_active],
        "flash_sales": [
            flash_payload(s)
            for s in sorted(product.flash_sales.all(), key=lambda s: s.starts_at)
            if s.ends_at > timezone.now()
        ],
    }


class MyProductSerializer(ProductSummarySerializer):
    status = serializers.ChoiceField(choices=Product.Status.choices)
    visibility = serializers.CharField()
    review_reason = serializers.CharField(allow_blank=True)
    matched_terms = serializers.ListField(child=serializers.CharField())
    description = serializers.CharField(allow_blank=True)
    description_voice = MediaSerializer(allow_null=True)
    video = MediaSerializer(allow_null=True)
    photos = MediaSerializer(many=True)
    base_price_minor = serializers.IntegerField()
    prep_days = serializers.IntegerField()
    variants = VariantSerializer(many=True)
    flash_sales = FlashSaleSerializer(many=True)


class VariantInputSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False, allow_null=True)
    shade = serializers.CharField(required=False, allow_blank=True, max_length=60)
    swatch = serializers.CharField(required=False, allow_blank=True, max_length=7)
    size = serializers.CharField(required=False, allow_blank=True, max_length=30)
    color = serializers.CharField(required=False, allow_blank=True, max_length=40)
    price_minor = serializers.IntegerField(required=False, allow_null=True)
    stock = serializers.IntegerField(min_value=0)


class ProductInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120)
    price_minor = serializers.IntegerField()
    category = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True, max_length=3000)
    prep_days = serializers.IntegerField(required=False, default=1)
    photos = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)
    video = serializers.UUIDField(required=False, allow_null=True)
    voice = serializers.UUIDField(required=False, allow_null=True)
    variants = VariantInputSerializer(many=True, required=False, default=list)


class StockInputSerializer(serializers.Serializer):
    stock = serializers.IntegerField(min_value=0)


class ShopSettingsInputSerializer(serializers.Serializer):
    is_open = serializers.BooleanField(required=False)
    pickup = serializers.BooleanField(required=False)
    pickup_note = serializers.CharField(required=False, allow_blank=True, max_length=300)
    seller_delivery = serializers.BooleanField(required=False)
    partner_delivery = serializers.BooleanField(required=False)
    partner_name = serializers.CharField(required=False, allow_blank=True, max_length=80)
    return_policy = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class ZoneInputSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=ZONE_MODES)
    name = serializers.CharField(max_length=80)
    fee_minor = serializers.IntegerField(min_value=0)


class MyShopSerializer(serializers.Serializer):
    shop = ShopBriefSerializer()
    delivery = DeliverySerializer()
    currency = serializers.CharField()
    can_sell = serializers.BooleanField()
    enabled = serializers.BooleanField()


def promo_payload(promo: PromoCode, uses: int) -> dict:
    return {
        "id": str(promo.pk),
        "code": promo.code,
        "percent_off": promo.percent_off,
        "amount_off_minor": promo.amount_off_minor,
        "currency": promo.currency,
        "min_order_minor": promo.min_order_minor,
        "starts_at": _iso(promo.starts_at),
        "ends_at": _iso(promo.ends_at),
        "max_uses": promo.max_uses,
        "max_per_client": promo.max_per_client,
        "is_active": promo.is_active,
        "uses": uses,
    }


class PromoSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    code = serializers.CharField()
    percent_off = serializers.IntegerField(allow_null=True)
    amount_off_minor = serializers.IntegerField(allow_null=True)
    currency = serializers.CharField()
    min_order_minor = serializers.IntegerField()
    starts_at = serializers.DateTimeField(allow_null=True)
    ends_at = serializers.DateTimeField(allow_null=True)
    max_uses = serializers.IntegerField(allow_null=True)
    max_per_client = serializers.IntegerField()
    is_active = serializers.BooleanField()
    uses = serializers.IntegerField()


class PromoInputSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=20)
    percent_off = serializers.IntegerField(required=False, allow_null=True)
    amount_off_minor = serializers.IntegerField(required=False, allow_null=True)
    min_order_minor = serializers.IntegerField(required=False, default=0)
    starts_at = serializers.DateTimeField(required=False, allow_null=True)
    ends_at = serializers.DateTimeField(required=False, allow_null=True)
    max_uses = serializers.IntegerField(required=False, allow_null=True)
    max_per_client = serializers.IntegerField(required=False, default=1)
    is_active = serializers.BooleanField(required=False, default=True)


class FlashSaleInputSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    percent_off = serializers.IntegerField()
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    quantity_limit = serializers.IntegerField(required=False, allow_null=True)


class BundleItemInputSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class BundleInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120)
    description = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    photo = serializers.UUIDField(required=False, allow_null=True)
    price_minor = serializers.IntegerField()
    items = BundleItemInputSerializer(many=True)
    is_active = serializers.BooleanField(required=False, default=True)


class FlashSaleRowSerializer(FlashSaleSerializer):
    product_id = serializers.UUIDField()
    product_title = serializers.CharField()


class PromotionsSerializer(serializers.Serializer):
    promos = PromoSerializer(many=True)
    bundles = BundleSerializer(many=True)
    flash_sales = FlashSaleRowSerializer(many=True)


class TopProductSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    title = serializers.CharField()
    quantity = serializers.IntegerField()
    amount_minor = serializers.IntegerField()


class LowStockSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    product_id = serializers.UUIDField()
    title = serializers.CharField()
    label = serializers.CharField(allow_blank=True)
    stock = serializers.IntegerField()


class StatsSerializer(serializers.Serializer):
    days = serializers.IntegerField()
    currency = serializers.CharField()
    orders = serializers.IntegerField()
    sales_minor = serializers.IntegerField()
    completed_minor = serializers.IntegerField()
    new = serializers.IntegerField()
    preparing = serializers.IntegerField()
    top = TopProductSerializer(many=True)
    running_out = LowStockSerializer(many=True)


# --- Cart and checkout ---------------------------------------------------------------------------


def cart_payload(shops) -> dict:
    result = []
    for cart in shops:
        result.append(
            {
                "shop": shop_brief(cart.pro),
                "pro_id": str(cart.pro.pk),
                "currency": cart.currency,
                "delivery": delivery_payload(cart.shop),
                "subtotal_minor": cart.subtotal_minor,
                "prep_days": cart.prep_days,
                "lines": [
                    {
                        "id": str(line.item.pk),
                        "kind": "bundle" if line.bundle is not None else "variant",
                        "product_id": str(line.product.pk) if line.product else None,
                        "product_slug": line.product.slug if line.product else None,
                        "variant_id": str(line.item.variant_id) if line.item.variant_id else None,
                        "bundle_id": str(line.item.bundle_id) if line.item.bundle_id else None,
                        "title": line.title,
                        "variant_label": line.variant_label,
                        "photo": _ready(line.photo),
                        "unit_price_minor": line.unit_price_minor,
                        "before_minor": line.base_price_minor
                        if line.base_price_minor != line.unit_price_minor
                        else None,
                        "quantity": line.quantity,
                        "total_minor": line.total_minor,
                        "stock_left": line.stock_left,
                        "available": line.available,
                        "flash_ends_at": _iso(line.flash_sale.ends_at) if line.flash_sale else None,
                    }
                    for line in cart.lines
                ],
            }
        )
    return {"shops": result, "count": sum(len(c.lines) for c in shops)}


class CartLineSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=["variant", "bundle"])
    product_id = serializers.UUIDField(allow_null=True)
    product_slug = serializers.CharField(allow_null=True)
    variant_id = serializers.UUIDField(allow_null=True)
    bundle_id = serializers.UUIDField(allow_null=True)
    title = serializers.CharField()
    variant_label = serializers.CharField(allow_blank=True)
    photo = MediaSerializer(allow_null=True)
    unit_price_minor = serializers.IntegerField()
    before_minor = serializers.IntegerField(allow_null=True)
    quantity = serializers.IntegerField()
    total_minor = serializers.IntegerField()
    stock_left = serializers.IntegerField()
    available = serializers.BooleanField()
    flash_ends_at = serializers.DateTimeField(allow_null=True)


class CartShopSerializer(serializers.Serializer):
    shop = ShopBriefSerializer()
    pro_id = serializers.UUIDField()
    currency = serializers.CharField()
    delivery = DeliverySerializer()
    subtotal_minor = serializers.IntegerField()
    prep_days = serializers.IntegerField()
    lines = CartLineSerializer(many=True)


class CartSerializer(serializers.Serializer):
    shops = CartShopSerializer(many=True)
    count = serializers.IntegerField()


class CartAddSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField(required=False, allow_null=True)
    bundle_id = serializers.UUIDField(required=False, allow_null=True)
    quantity = serializers.IntegerField(min_value=1, default=1)
    sale_live_id = serializers.UUIDField(
        required=False, allow_null=True, help_text="Added during this sales live."
    )

    def validate(self, attrs):
        if bool(attrs.get("variant_id")) == bool(attrs.get("bundle_id")):
            raise serializers.ValidationError("variant_id or bundle_id")
        return attrs


class QuantitySerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=0)


class ShopChoiceSerializer(serializers.Serializer):
    pro_id = serializers.UUIDField()
    delivery_mode = serializers.ChoiceField(choices=DeliveryMode.choices)
    zone_id = serializers.UUIDField(required=False, allow_null=True)
    promo_code = serializers.CharField(required=False, allow_blank=True, max_length=20)
    note = serializers.CharField(required=False, allow_blank=True, max_length=300)


class QuoteInputSerializer(serializers.Serializer):
    shops = ShopChoiceSerializer(many=True)


class CheckoutInputSerializer(QuoteInputSerializer):
    address = serializers.CharField(required=False, allow_blank=True, max_length=255)
    landmarks = serializers.CharField(required=False, allow_blank=True, max_length=500)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)


def quote_payload(quotes) -> dict:
    rows = [
        {
            "pro_id": str(q.cart.pro.pk),
            "shop": q.cart.pro.display_name,
            "delivery_mode": q.mode,
            "zone": q.zone.name if q.zone else "",
            "promo_code": q.promo.code if q.promo else "",
            "subtotal_minor": q.subtotal_minor,
            "discount_minor": q.discount_minor,
            "items_minor": q.items_minor,
            "delivery_minor": q.delivery_minor,
            "buyer_fee_minor": q.buyer_fee_minor,
            "total_minor": q.total_minor,
            "prep_days": q.cart.prep_days,
        }
        for q in quotes
    ]
    return {
        "currency": quotes[0].cart.currency,
        "orders": rows,
        "total_minor": sum(q.total_minor for q in quotes),
    }


class QuoteRowSerializer(serializers.Serializer):
    pro_id = serializers.UUIDField()
    shop = serializers.CharField()
    delivery_mode = serializers.ChoiceField(choices=DeliveryMode.choices)
    zone = serializers.CharField(allow_blank=True)
    promo_code = serializers.CharField(allow_blank=True)
    subtotal_minor = serializers.IntegerField()
    discount_minor = serializers.IntegerField()
    items_minor = serializers.IntegerField()
    delivery_minor = serializers.IntegerField()
    buyer_fee_minor = serializers.IntegerField()
    total_minor = serializers.IntegerField()
    prep_days = serializers.IntegerField()


class QuoteSerializer(serializers.Serializer):
    currency = serializers.CharField()
    orders = QuoteRowSerializer(many=True)
    total_minor = serializers.IntegerField()


class CheckoutResultSerializer(serializers.Serializer):
    group_id = serializers.UUIDField()
    checkout_url = serializers.CharField(allow_blank=True)
    orders = serializers.ListField(child=serializers.UUIDField())


# --- Orders --------------------------------------------------------------------------------------


def order_payload(order: Order, viewer, *, with_payment: bool = True) -> dict:
    is_seller = order.pro.user_id == viewer.pk
    payment = order.payment
    status = order.status
    OS = Order.Status
    pickup = order.delivery_mode == DeliveryMode.PICKUP
    pro = order.pro
    return {
        "id": str(order.pk),
        "reference": order.reference,
        "status": status,
        "role": "seller" if is_seller else "buyer",
        "created_at": _iso(order.created_at),
        "currency": order.currency,
        "subtotal_minor": order.subtotal_minor,
        "discount_minor": order.discount_minor,
        "items_minor": order.items_minor,
        "delivery_minor": order.delivery_minor,
        "buyer_fee_minor": payment.buyer_fee_minor,
        "total_minor": payment.total_minor,
        "promo_code": order.promo_label,
        "delivery_mode": order.delivery_mode,
        "zone_name": order.zone_name,
        "partner_name": order.partner_name,
        # The address and phone are for the seller (and the client herself) only.
        "address": order.address,
        "landmarks": order.landmarks,
        "contact_phone": order.contact_phone,
        "note": order.note,
        "prep_days": order.prep_days,
        "preparing_at": _iso(order.preparing_at),
        "completed_at": _iso(order.completed_at),
        "cancelled_at": _iso(order.cancelled_at),
        "shipping_proof": _ready(order.shipping_proof),
        "shop": shop_brief(pro),
        "pickup": {
            "address": pro.address if pro.receives_clients else "",
            "city": pro.city,
            "district": pro.district,
            "landmarks": pro.landmarks,
            "landmarks_voice": _ready(pro.landmarks_voice),
            "itinerary_video": _ready(pro.itinerary_video),
            "note": getattr(getattr(pro, "shop", None), "pickup_note", ""),
            "latitude": pro.location.y if pro.location and pro.receives_clients else None,
            "longitude": pro.location.x if pro.location and pro.receives_clients else None,
        }
        if pickup
        else None,
        "buyer": person_payload(order.buyer),
        "lines": [
            {
                "id": str(line.pk),
                "title": line.title,
                "variant_label": line.variant_label,
                "photo": _ready(line.photo),
                "unit_price_minor": line.unit_price_minor,
                "quantity": line.quantity,
                "total_minor": line.total_minor,
                "product_id": str(line.product_id) if line.product_id else None,
                "is_bundle": line.bundle_id is not None or bool(line.components),
            }
            for line in order.lines.all()
        ],
        "payment": payment_payload(payment, viewer) if with_payment else None,
        "can": {
            "prepare": is_seller and status == OS.NEW,
            "ship": is_seller and status in (OS.NEW, OS.PREPARING) and not pickup,
            "ready": is_seller and status in (OS.NEW, OS.PREPARING) and pickup,
            "cancel": (is_seller and status in (OS.NEW, OS.PREPARING))
            or (not is_seller and status == OS.NEW),
            "pay": not is_seller and status == OS.PENDING_PAYMENT,
        },
    }


class OrderLineSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    variant_label = serializers.CharField(allow_blank=True)
    photo = MediaSerializer(allow_null=True)
    unit_price_minor = serializers.IntegerField()
    quantity = serializers.IntegerField()
    total_minor = serializers.IntegerField()
    product_id = serializers.UUIDField(allow_null=True)
    is_bundle = serializers.BooleanField()


class PickupSerializer(serializers.Serializer):
    address = serializers.CharField(allow_blank=True)
    city = serializers.CharField(allow_blank=True)
    district = serializers.CharField(allow_blank=True)
    landmarks = serializers.CharField(allow_blank=True)
    landmarks_voice = MediaSerializer(allow_null=True)
    itinerary_video = MediaSerializer(allow_null=True)
    note = serializers.CharField(allow_blank=True)
    latitude = serializers.FloatField(allow_null=True)
    longitude = serializers.FloatField(allow_null=True)


class OrderAbilitiesSerializer(serializers.Serializer):
    prepare = serializers.BooleanField()
    ship = serializers.BooleanField()
    ready = serializers.BooleanField()
    cancel = serializers.BooleanField()
    pay = serializers.BooleanField()


class OrderSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    reference = serializers.CharField()
    status = serializers.ChoiceField(choices=Order.Status.choices)
    role = serializers.ChoiceField(choices=["buyer", "seller"])
    created_at = serializers.DateTimeField()
    currency = serializers.CharField()
    subtotal_minor = serializers.IntegerField()
    discount_minor = serializers.IntegerField()
    items_minor = serializers.IntegerField()
    delivery_minor = serializers.IntegerField()
    buyer_fee_minor = serializers.IntegerField()
    total_minor = serializers.IntegerField()
    promo_code = serializers.CharField(allow_blank=True)
    delivery_mode = serializers.ChoiceField(choices=DeliveryMode.choices)
    zone_name = serializers.CharField(allow_blank=True)
    partner_name = serializers.CharField(allow_blank=True)
    address = serializers.CharField(allow_blank=True)
    landmarks = serializers.CharField(allow_blank=True)
    contact_phone = serializers.CharField(allow_blank=True)
    note = serializers.CharField(allow_blank=True)
    prep_days = serializers.IntegerField()
    preparing_at = serializers.DateTimeField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    cancelled_at = serializers.DateTimeField(allow_null=True)
    shipping_proof = MediaSerializer(allow_null=True)
    shop = ShopBriefSerializer()
    pickup = PickupSerializer(allow_null=True)
    buyer = PersonSerializer()
    lines = OrderLineSerializer(many=True)
    payment = PaymentSerializer(allow_null=True)
    can = OrderAbilitiesSerializer()


class OrderListSerializer(serializers.Serializer):
    results = OrderSerializer(many=True)


class ShipInputSerializer(serializers.Serializer):
    proof = serializers.UUIDField()
    carrier = serializers.CharField(required=False, allow_blank=True, max_length=80)
    tracking_number = serializers.CharField(required=False, allow_blank=True, max_length=80)


class WishlistSerializer(serializers.Serializer):
    results = ProductSummarySerializer(many=True)


class ProductReviewSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    rating = serializers.IntegerField()
    text = serializers.CharField(allow_blank=True)
    author = serializers.CharField()
    photo = MediaSerializer(allow_null=True)
    voice = MediaSerializer(allow_null=True)
    reply = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()


class ProductReviewsSerializer(serializers.Serializer):
    average = serializers.FloatField(allow_null=True)
    count = serializers.IntegerField()
    results = ProductReviewSerializer(many=True)


# --- Sales lives -----------------------------------------------------------------------------


class MySaleLiveSerializer(ShopLiveSerializer):
    description = serializers.CharField()
    duration_minutes = serializers.IntegerField()
    orders_count = serializers.IntegerField()
    revenue_minor = serializers.IntegerField()
    currency = serializers.CharField()
    peak_viewers = serializers.IntegerField()
    total_viewers = serializers.IntegerField()


class MySaleLivesSerializer(serializers.Serializer):
    results = MySaleLiveSerializer(many=True)
    quota = LiveQuotaSerializer()
    open = serializers.BooleanField(help_text="Sales lives are open in her country.")
    can_sell = serializers.BooleanField(help_text="Her shop is verified (needed to go live).")


class SaleLiveInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    starts_at = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField(min_value=15, max_value=480)
