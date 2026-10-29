from __future__ import annotations

from django.db.models import Case, IntegerField, Value, When
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttling import SettingRateThrottle
from apps.accounts.views_base import OptionalAuthView

from . import errors, selectors, services
from . import serializers as s
from .models import Aisle, ShippingMode, SpecialRequest

# Small prices first, then trending, then luxury (not the alphabetical order).
AISLE_ORDER = Case(
    *(When(aisle=key, then=Value(rank)) for rank, key in enumerate(Aisle.values)),
    output_field=IntegerField(),
)


class SelectionWriteView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "selection"

    def get_throttles(self):
        return super().get_throttles() if self.request.method != "GET" else []


class ProductListView(OptionalAuthView):
    """The three aisles of the France Selection (final prices in FCFA)."""

    @extend_schema(
        tags=["selection"],
        operation_id="selection_products_list",
        parameters=[OpenApiParameter("aisle", str, enum=list(Aisle.values), required=False)],
        responses=s.SelectionProductListSerializer,
    )
    def get(self, request):
        rows = selectors.on_sale()
        aisle = request.query_params.get("aisle")
        if aisle in Aisle.values:
            rows = rows.filter(aisle=aisle)
        return Response(
            {
                "results": [
                    s.product_summary(p)
                    for p in rows.annotate(rank=AISLE_ORDER).order_by("rank", "-created_at")
                ],
                "grouped": s._estimate(ShippingMode.GROUPED),
                "express": s._estimate(ShippingMode.EXPRESS),
            }
        )


class ProductView(OptionalAuthView):
    @extend_schema(tags=["selection"], responses=s.SelectionProductDetailSerializer)
    def get(self, request, slug):
        product = selectors.on_sale().filter(slug=slug).first()
        if product is None:
            raise errors.ProductNotFound()
        return Response(s.product_detail(product))


class PickupPointsView(OptionalAuthView):
    @extend_schema(tags=["selection"], responses=s.SelectionPickupPointSerializer(many=True))
    def get(self, request):
        return Response([s.point_payload(p) for p in selectors.pickup_points()])


def _order(request, order_id):
    order = selectors.order_for(request.user, order_id)
    if order is None:
        raise errors.OrderNotFound()
    return order


def _answer(request, order_id, code=status.HTTP_200_OK) -> Response:
    return Response(s.order_payload(_order(request, order_id), request.user), status=code)


class OrdersView(SelectionWriteView):
    @extend_schema(
        tags=["selection"],
        operation_id="selection_orders_list",
        responses=s.SelectionOrderListSerializer,
    )
    def get(self, request):
        rows = selectors.orders_of(request.user)[:50]
        return Response(
            {"results": [s.order_payload(o, request.user, with_payment=False) for o in rows]}
        )

    @extend_schema(
        tags=["selection"],
        request=s.SelectionOrderInputSerializer,
        responses={201: s.SelectionOrderSerializer},
    )
    def post(self, request):
        data = s.SelectionOrderInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        order = services.place_order(
            request.user,
            values["product_id"],
            shipping_mode=values["shipping_mode"],
            pickup_point_id=values["pickup_point_id"],
            option=values.get("option", ""),
            quantity=values["quantity"],
            group=values["group"],
            voucher=values["voucher"],
        )
        services.start_payment(order, request.user)
        return _answer(request, order.pk, status.HTTP_201_CREATED)


class OrderView(SelectionWriteView):
    @extend_schema(tags=["selection"], responses=s.SelectionOrderSerializer)
    def get(self, request, order_id):
        return _answer(request, order_id)


class OrderCancelView(SelectionWriteView):
    @extend_schema(tags=["selection"], request=None, responses=s.SelectionOrderSerializer)
    def post(self, request, order_id):
        services.cancel(request.user, _order(request, order_id))
        return _answer(request, order_id)


class OrderPayView(SelectionWriteView):
    @extend_schema(tags=["selection"], request=None, responses=s.SelectionOrderSerializer)
    def post(self, request, order_id):
        services.start_payment(_order(request, order_id), request.user)
        return _answer(request, order_id)


def _request(request, request_id) -> SpecialRequest:
    found = SpecialRequest.objects.filter(pk=request_id, client=request.user).first()
    if found is None:
        raise errors.RequestNotFound()
    return found


class RequestsView(SelectionWriteView):
    @extend_schema(tags=["selection"], responses=s.SelectionRequestSerializer(many=True))
    def get(self, request):
        rows = SpecialRequest.objects.filter(client=request.user).select_related(
            "photo", "category", "order"
        )[:30]
        return Response([s.request_payload(r) for r in rows])

    @extend_schema(
        tags=["selection"],
        request=s.SelectionRequestInputSerializer,
        responses={201: s.SelectionRequestSerializer},
    )
    def post(self, request):
        data = s.SelectionRequestInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        created = services.create_request(
            request.user,
            link=values.get("link", ""),
            photo_id=values.get("photo"),
            note=values.get("note", ""),
        )
        return Response(s.request_payload(created), status=status.HTTP_201_CREATED)


class RequestOrderView(SelectionWriteView):
    """She accepts the quote: an order to pay."""

    @extend_schema(
        tags=["selection"],
        request=s.SelectionQuoteOrderSerializer,
        responses={201: s.SelectionOrderSerializer},
    )
    def post(self, request, request_id):
        data = s.SelectionQuoteOrderSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        order = services.order_quote(
            request.user,
            _request(request, request_id),
            shipping_mode=data.validated_data["shipping_mode"],
            pickup_point_id=data.validated_data["pickup_point_id"],
        )
        services.start_payment(order, request.user)
        return _answer(request, order.pk, status.HTTP_201_CREATED)


class RequestDeclineView(SelectionWriteView):
    @extend_schema(tags=["selection"], request=None, responses=s.SelectionRequestSerializer)
    def post(self, request, request_id):
        found = services.decline(request.user, _request(request, request_id))
        return Response(s.request_payload(found))
