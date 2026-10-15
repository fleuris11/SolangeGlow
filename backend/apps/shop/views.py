from __future__ import annotations

from django.db.models import Avg, Count
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttling import SettingRateThrottle
from apps.accounts.views_base import OptionalAuthView
from apps.payments import services as payment_services
from apps.pros.models import ProProfile
from apps.pros.selectors import can_collect_payments
from apps.social.models import Review, Visibility

from . import errors, selectors
from . import serializers as s
from .models import (
    Category,
    FlashSale,
    Order,
    OrderLine,
    PromoCode,
    StockAlert,
    WishlistItem,
)
from .services import alerts, cart, catalog, checkout, orders, promotions


def _wished(user, products) -> frozenset:
    if user is None or not user.is_authenticated:
        return frozenset()
    return frozenset(
        WishlistItem.objects.filter(user=user, product__in=products).values_list(
            "product_id", flat=True
        )
    )


def _detail(request, product) -> Response:
    user = request.user
    signed_in = user is not None and user.is_authenticated
    wished = signed_in and WishlistItem.objects.filter(user=user, product=product).exists()
    watching = (
        StockAlert.objects.filter(user=user, variant__product=product).values_list(
            "variant_id", flat=True
        )
        if signed_in
        else []
    )
    return Response(s.product_detail(product, user, wished=wished, watching=list(watching)))


class ShopWriteView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "shop"

    def get_throttles(self):
        return super().get_throttles() if self.request.method != "GET" else []


# --- Public: the shop of a pro, a product ---------------------------------------------------------


class CategoriesView(OptionalAuthView):
    @extend_schema(tags=["shop"], responses=s.ProductCategorySerializer(many=True))
    def get(self, request):
        rows = Category.objects.filter(is_active=True)
        return Response([s.category_payload(c) for c in rows])


class ShopPageView(OptionalAuthView):
    """The « Shop » tab of a showcase: products on sale, bundles, how to receive them."""

    @extend_schema(
        tags=["shop"],
        parameters=[OpenApiParameter("category", str, required=False)],
        responses=s.ShopPageSerializer,
    )
    def get(self, request, slug):
        pro = ProProfile.objects.filter(slug=slug, status=ProProfile.Status.PUBLISHED).first()
        if pro is None or not selectors.shop_enabled(pro.country):
            raise errors.ProductNotFound()
        products = list(
            selectors.products_of_shop(pro, category=request.query_params.get("category"))
        )
        shop = selectors.shop_of(pro)
        wished = _wished(request.user, products)
        categories = {p.category.key: p.category for p in products if p.category_id}
        bundles = [b for b in selectors.bundles_on_sale(pro) if selectors.bundle_is_sellable(b)]
        return Response(
            {
                "shop": s.shop_brief(pro),
                "delivery": s.delivery_payload(shop),
                "categories": [
                    s.category_payload(c)
                    for c in sorted(categories.values(), key=lambda c: (c.position, c.key))
                ],
                "products": [s.product_summary(p, wished=wished) for p in products],
                "bundles": [s.bundle_payload(b) for b in bundles],
            }
        )


class ProductBySlugView(OptionalAuthView):
    @extend_schema(
        tags=["shop"], operation_id="shop_product_by_slug", responses=s.ProductDetailSerializer
    )
    def get(self, request, slug, product_slug):
        product = selectors.product_by_slug(slug, product_slug)
        if product is None or not selectors.shop_enabled(product.pro.country):
            raise errors.ProductNotFound()
        return _detail(request, product)


class ProductView(OptionalAuthView):
    @extend_schema(tags=["shop"], responses=s.ProductDetailSerializer)
    def get(self, request, product_id):
        product = selectors.product_on_sale(product_id)
        if product is None:
            raise errors.ProductNotFound()
        return _detail(request, product)


class ProductReviewsView(OptionalAuthView):
    """Verified reviews left after orders that contained this product."""

    @extend_schema(tags=["shop"], responses=s.ProductReviewsSerializer)
    def get(self, request, product_id):
        order_ids = OrderLine.objects.filter(product_id=product_id).values("order_id")
        reviews = Review.objects.filter(
            source_type="order", source_id__in=order_ids, visibility=Visibility.VISIBLE
        )
        stats = reviews.aggregate(average=Avg("rating"), count=Count("pk"))
        rows = reviews.select_related("author", "photo", "voice").order_by("-created_at")[:20]
        return Response(
            {
                "average": round(float(stats["average"]), 2) if stats["average"] else None,
                "count": stats["count"],
                "results": [
                    {
                        "id": str(r.pk),
                        "rating": r.rating,
                        "text": r.text,
                        "author": r.author.first_name,
                        "photo": s._ready(r.photo),
                        "voice": s._ready(r.voice),
                        "reply": r.reply,
                        "created_at": r.created_at.isoformat(),
                    }
                    for r in rows
                ],
            }
        )


# --- Cart and checkout ---------------------------------------------------------------------------


def _cart_answer(user, code=status.HTTP_200_OK) -> Response:
    return Response(s.cart_payload(cart.cart_summary(user)), status=code)


class CartView(ShopWriteView):
    @extend_schema(tags=["shop"], responses=s.CartSerializer)
    def get(self, request):
        return _cart_answer(request.user)


class CartItemsView(ShopWriteView):
    @extend_schema(tags=["shop"], request=s.CartAddSerializer, responses={201: s.CartSerializer})
    def post(self, request):
        data = s.CartAddSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        cart.add(
            request.user,
            variant_id=values.get("variant_id"),
            bundle_id=values.get("bundle_id"),
            quantity=values["quantity"],
        )
        return _cart_answer(request.user, status.HTTP_201_CREATED)


class CartItemView(ShopWriteView):
    @extend_schema(tags=["shop"], request=s.QuantitySerializer, responses=s.CartSerializer)
    def patch(self, request, item_id):
        data = s.QuantitySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        cart.set_quantity(request.user, item_id, data.validated_data["quantity"])
        return _cart_answer(request.user)

    @extend_schema(tags=["shop"], request=None, responses={200: s.CartSerializer})
    def delete(self, request, item_id):
        cart.set_quantity(request.user, item_id, 0)
        return _cart_answer(request.user)


def _choices(values) -> list[checkout.ShopChoice]:
    return [
        checkout.ShopChoice(
            pro_id=row["pro_id"],
            delivery_mode=row["delivery_mode"],
            zone_id=row.get("zone_id"),
            promo_code=row.get("promo_code", ""),
            note=row.get("note", ""),
        )
        for row in values["shops"]
    ]


class QuoteView(ShopWriteView):
    """Step 2 of the checkout: what each order costs, buyer protection included."""

    @extend_schema(tags=["shop"], request=s.QuoteInputSerializer, responses=s.QuoteSerializer)
    def post(self, request):
        data = s.QuoteInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        quotes = checkout.quote(request.user, _choices(data.validated_data))
        return Response(s.quote_payload(quotes))


class CheckoutView(ShopWriteView):
    """Creates the orders and their grouped payment, and opens the payment page."""

    @extend_schema(
        tags=["shop"],
        request=s.CheckoutInputSerializer,
        responses={201: s.CheckoutResultSerializer},
    )
    def post(self, request):
        data = s.CheckoutInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        group, placed = checkout.place_orders(
            request.user,
            _choices(values),
            address=values.get("address", ""),
            landmarks=values.get("landmarks", ""),
            phone=values.get("phone", ""),
        )
        group = payment_services.start_group_checkout(group, buyer=request.user)
        return Response(
            {
                "group_id": str(group.pk),
                "checkout_url": group.checkout_url,
                "orders": [str(o.pk) for o in placed],
            },
            status=status.HTTP_201_CREATED,
        )


# --- Orders --------------------------------------------------------------------------------------


def _order(request, order_id) -> Order:
    order = selectors.order_for(request.user, order_id)
    if order is None:
        raise errors.OrderNotFound()
    return order


def _order_answer(request, order_id) -> Response:
    return Response(s.order_payload(_order(request, order_id), request.user))


class OrderListView(ShopWriteView):
    @extend_schema(
        tags=["shop"],
        operation_id="shop_orders_list",
        parameters=[
            OpenApiParameter("role", str, enum=["buyer", "seller"], required=False),
            OpenApiParameter("status", str, required=False),
        ],
        responses=s.OrderListSerializer,
    )
    def get(self, request):
        role = "seller" if request.query_params.get("role") == "seller" else "buyer"
        rows = selectors.orders_of(
            request.user, role=role, status=request.query_params.get("status") or None
        )[:50]
        return Response(
            {"results": [s.order_payload(o, request.user, with_payment=False) for o in rows]}
        )


class OrderView(ShopWriteView):
    @extend_schema(tags=["shop"], responses=s.OrderSerializer)
    def get(self, request, order_id):
        return _order_answer(request, order_id)


class OrderPrepareView(ShopWriteView):
    @extend_schema(tags=["shop"], request=None, responses=s.OrderSerializer)
    def post(self, request, order_id):
        orders.start_preparing(request.user, _order(request, order_id))
        return _order_answer(request, order_id)


class OrderShipView(ShopWriteView):
    @extend_schema(tags=["shop"], request=s.ShipInputSerializer, responses=s.OrderSerializer)
    def post(self, request, order_id):
        data = s.ShipInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        orders.ship(
            request.user,
            _order(request, order_id),
            proof_media_id=values["proof"],
            carrier=values.get("carrier", ""),
            tracking_number=values.get("tracking_number", ""),
        )
        return _order_answer(request, order_id)


class OrderReadyView(ShopWriteView):
    @extend_schema(tags=["shop"], request=None, responses=s.OrderSerializer)
    def post(self, request, order_id):
        orders.ready_for_pickup(request.user, _order(request, order_id))
        return _order_answer(request, order_id)


class OrderCancelView(ShopWriteView):
    @extend_schema(tags=["shop"], request=None, responses=s.OrderSerializer)
    def post(self, request, order_id):
        orders.cancel(request.user, _order(request, order_id))
        return _order_answer(request, order_id)


class OrderPayView(ShopWriteView):
    """The payment page again (the client left it before paying)."""

    @extend_schema(tags=["shop"], request=None, responses=s.CheckoutResultSerializer)
    def post(self, request, order_id):
        order = _order(request, order_id)
        if order.buyer_id != request.user.pk or order.payment.group_id is None:
            raise errors.OrderNotFound()
        group = payment_services.start_group_checkout(order.payment.group, buyer=request.user)
        return Response(
            {
                "group_id": str(group.pk),
                "checkout_url": group.checkout_url,
                "orders": [
                    str(o)
                    for o in Order.objects.filter(payment__group=group).values_list("pk", flat=True)
                ],
            }
        )


# --- Wishlist and alerts -------------------------------------------------------------------------


class WishlistView(ShopWriteView):
    @extend_schema(tags=["shop"], responses=s.WishlistSerializer)
    def get(self, request):
        items = WishlistItem.objects.filter(user=request.user).values_list("product_id", flat=True)
        products = list(selectors.products_in(list(items)))
        wished = frozenset(p.pk for p in products)
        return Response({"results": [s.product_summary(p, wished=wished) for p in products]})


class WishlistItemView(ShopWriteView):
    @extend_schema(tags=["shop"], request=None, responses={204: None})
    def put(self, request, product_id):
        alerts.add_to_wishlist(request.user, product_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(tags=["shop"], request=None, responses={204: None})
    def delete(self, request, product_id):
        alerts.remove_from_wishlist(request.user, product_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class StockAlertView(ShopWriteView):
    @extend_schema(tags=["shop"], request=None, responses={204: None})
    def put(self, request, variant_id):
        alerts.watch_stock(request.user, variant_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(tags=["shop"], request=None, responses={204: None})
    def delete(self, request, variant_id):
        alerts.unwatch_stock(request.user, variant_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- « My shop » (the pro) -----------------------------------------------------------------------


def _my_shop(user) -> dict:
    pro = catalog.pro_of(user)
    return {
        "shop": s.shop_brief(pro),
        "delivery": s.delivery_payload(selectors.shop_of(pro)),
        "currency": pro.currency or "XOF",
        "can_sell": can_collect_payments(pro),
        "enabled": selectors.shop_enabled(pro.country),
    }


class MyShopView(ShopWriteView):
    @extend_schema(tags=["my-shop"], responses=s.MyShopSerializer)
    def get(self, request):
        return Response(_my_shop(request.user))

    @extend_schema(
        tags=["my-shop"], request=s.ShopSettingsInputSerializer, responses=s.MyShopSerializer
    )
    def patch(self, request):
        data = s.ShopSettingsInputSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        catalog.update_shop(request.user, **data.validated_data)
        return Response(_my_shop(request.user))


class ZonesView(ShopWriteView):
    @extend_schema(
        tags=["my-shop"], request=s.ZoneInputSerializer, responses={201: s.MyShopSerializer}
    )
    def post(self, request):
        data = s.ZoneInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        catalog.save_zone(request.user, **data.validated_data)
        return Response(_my_shop(request.user), status=status.HTTP_201_CREATED)


class ZoneView(ShopWriteView):
    @extend_schema(tags=["my-shop"], request=s.ZoneInputSerializer, responses=s.MyShopSerializer)
    def patch(self, request, zone_id):
        data = s.ZoneInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        catalog.save_zone(request.user, zone_id=zone_id, **data.validated_data)
        return Response(_my_shop(request.user))

    @extend_schema(tags=["my-shop"], request=None, responses={200: s.MyShopSerializer})
    def delete(self, request, zone_id):
        catalog.delete_zone(request.user, zone_id)
        return Response(_my_shop(request.user))


def _save_product(request, product=None):
    data = s.ProductInputSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    values = data.validated_data
    return catalog.save_product(
        request.user,
        product=product,
        title=values["title"],
        price_minor=values["price_minor"],
        category_key=values.get("category") or None,
        description=values.get("description", ""),
        prep_days=values["prep_days"],
        photo_ids=values["photos"],
        video_id=values.get("video"),
        voice_id=values.get("voice"),
        variants=[dict(row) for row in values["variants"]],
    )


def _my_product(request, product_id):
    product = selectors.my_product(catalog.pro_of(request.user), product_id)
    if product is None:
        raise errors.ProductNotFound()
    return product


def _my_product_answer(request, product_id, code=status.HTTP_200_OK) -> Response:
    product = selectors.my_products(catalog.pro_of(request.user)).get(pk=product_id)
    return Response(s.my_product_payload(product), status=code)


class MyProductsView(ShopWriteView):
    @extend_schema(tags=["my-shop"], responses=s.MyProductSerializer(many=True))
    def get(self, request):
        rows = selectors.my_products(catalog.pro_of(request.user))
        return Response([s.my_product_payload(p) for p in rows])

    @extend_schema(
        tags=["my-shop"], request=s.ProductInputSerializer, responses={201: s.MyProductSerializer}
    )
    def post(self, request):
        product = _save_product(request)
        return _my_product_answer(request, product.pk, status.HTTP_201_CREATED)


class MyProductView(ShopWriteView):
    @extend_schema(tags=["my-shop"], responses=s.MyProductSerializer)
    def get(self, request, product_id):
        _my_product(request, product_id)
        return _my_product_answer(request, product_id)

    @extend_schema(
        tags=["my-shop"], request=s.ProductInputSerializer, responses=s.MyProductSerializer
    )
    def put(self, request, product_id):
        _save_product(request, _my_product(request, product_id))
        return _my_product_answer(request, product_id)

    @extend_schema(tags=["my-shop"], request=None, responses={204: None})
    def delete(self, request, product_id):
        catalog.archive(request.user, _my_product(request, product_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublishProductView(ShopWriteView):
    @extend_schema(tags=["my-shop"], request=None, responses=s.MyProductSerializer)
    def post(self, request, product_id):
        catalog.publish(request.user, _my_product(request, product_id))
        return _my_product_answer(request, product_id)


class PauseProductView(ShopWriteView):
    @extend_schema(tags=["my-shop"], request=None, responses=s.MyProductSerializer)
    def post(self, request, product_id):
        catalog.pause(request.user, _my_product(request, product_id))
        return _my_product_answer(request, product_id)


class VariantStockView(ShopWriteView):
    @extend_schema(tags=["my-shop"], request=s.StockInputSerializer, responses=s.VariantSerializer)
    def patch(self, request, variant_id):
        data = s.StockInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        variant = catalog.set_stock(request.user, variant_id, data.validated_data["stock"])
        return Response(s.variant_payload(variant, None))


def _promotions(user) -> dict:
    pro = catalog.pro_of(user)
    now = timezone.now()
    sales = (
        FlashSale.objects.filter(product__pro=pro, ends_at__gt=now)
        .select_related("product")
        .order_by("starts_at")
    )
    return {
        "promos": [
            s.promo_payload(p, promotions.uses_of(p))
            for p in PromoCode.objects.filter(pro=pro).order_by("-created_at")
        ],
        "bundles": [s.bundle_payload(b) for b in selectors.my_bundles(pro)],
        "flash_sales": [
            {
                **s.flash_payload(sale),
                "product_id": str(sale.product_id),
                "product_title": sale.product.title,
            }
            for sale in sales
        ],
    }


class PromotionsView(ShopWriteView):
    @extend_schema(tags=["my-shop"], responses=s.PromotionsSerializer)
    def get(self, request):
        return Response(_promotions(request.user))


class PromosView(ShopWriteView):
    @extend_schema(
        tags=["my-shop"], request=s.PromoInputSerializer, responses={201: s.PromotionsSerializer}
    )
    def post(self, request):
        data = s.PromoInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        promotions.save_promo(request.user, **data.validated_data)
        return Response(_promotions(request.user), status=status.HTTP_201_CREATED)


class PromoView(ShopWriteView):
    @extend_schema(
        tags=["my-shop"], request=s.PromoInputSerializer, responses=s.PromotionsSerializer
    )
    def patch(self, request, promo_id):
        data = s.PromoInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        promotions.save_promo(request.user, promo_id=promo_id, **data.validated_data)
        return Response(_promotions(request.user))

    @extend_schema(tags=["my-shop"], request=None, responses={200: s.PromotionsSerializer})
    def delete(self, request, promo_id):
        promotions.delete_promo(request.user, promo_id)
        return Response(_promotions(request.user))


class FlashSalesView(ShopWriteView):
    @extend_schema(
        tags=["my-shop"],
        request=s.FlashSaleInputSerializer,
        responses={201: s.PromotionsSerializer},
    )
    def post(self, request):
        data = s.FlashSaleInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        promotions.create_flash_sale(request.user, **data.validated_data)
        return Response(_promotions(request.user), status=status.HTTP_201_CREATED)


class FlashSaleView(ShopWriteView):
    @extend_schema(tags=["my-shop"], request=None, responses={200: s.PromotionsSerializer})
    def delete(self, request, sale_id):
        promotions.end_flash_sale(request.user, sale_id)
        return Response(_promotions(request.user))


def _bundle_values(request) -> dict:
    data = s.BundleInputSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    values = dict(data.validated_data)
    values["photo_id"] = values.pop("photo", None)
    values["items"] = [dict(item) for item in values["items"]]
    return values


class BundlesView(ShopWriteView):
    @extend_schema(
        tags=["my-shop"], request=s.BundleInputSerializer, responses={201: s.PromotionsSerializer}
    )
    def post(self, request):
        promotions.save_bundle(request.user, **_bundle_values(request))
        return Response(_promotions(request.user), status=status.HTTP_201_CREATED)


class BundleView(ShopWriteView):
    @extend_schema(
        tags=["my-shop"], request=s.BundleInputSerializer, responses=s.PromotionsSerializer
    )
    def patch(self, request, bundle_id):
        promotions.save_bundle(request.user, bundle_id=bundle_id, **_bundle_values(request))
        return Response(_promotions(request.user))

    @extend_schema(tags=["my-shop"], request=None, responses={200: s.PromotionsSerializer})
    def delete(self, request, bundle_id):
        promotions.delete_bundle(request.user, bundle_id)
        return Response(_promotions(request.user))


class StatsView(ShopWriteView):
    @extend_schema(tags=["my-shop"], responses=s.StatsSerializer)
    def get(self, request):
        data = selectors.stats(catalog.pro_of(request.user))
        data["running_out"] = [
            {
                "variant_id": str(v.pk),
                "product_id": str(v.product_id),
                "title": v.product.title,
                "label": v.label,
                "stock": v.stock,
            }
            for v in data["running_out"]
        ]
        return Response(data)
