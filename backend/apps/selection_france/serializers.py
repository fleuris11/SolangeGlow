from __future__ import annotations

from rest_framework import serializers

from apps.core.media.api import MediaSerializer
from apps.core.media.services import asset_payload
from apps.payments.serializers import PaymentSerializer, payment_payload

from . import selectors, services
from .models import Aisle, SelectionOrder, SelectionProduct, ShippingMode, SpecialRequest


def _iso(value):
    return value.isoformat() if value else None


def _estimate(mode, after=None) -> dict:
    first, last = selectors.estimate(mode, after=after)
    return {"from": first.isoformat(), "to": last.isoformat()}


class SelectionEstimateSerializer(serializers.Serializer):
    # « from » is a Python keyword: declared through the fields mapping.
    def get_fields(self):
        return {"from": serializers.DateField(), "to": serializers.DateField()}


class SelectionCategorySerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()
    air_restricted = serializers.BooleanField()


def group_payload(product) -> dict | None:
    group = selectors.open_group(product)
    if group is None:
        return None
    return {
        "id": str(group.pk),
        "price_xof": group.price_xof,
        "target": group.target_quantity,
        "count": selectors.group_count(group),
        "ends_at": _iso(group.ends_at),
    }


class SelectionGroupSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    price_xof = serializers.IntegerField()
    target = serializers.IntegerField()
    count = serializers.IntegerField()
    ends_at = serializers.DateTimeField()


def product_summary(product: SelectionProduct) -> dict:
    photo = next(iter(product.photos.all()), None)
    return {
        "id": str(product.pk),
        "slug": product.slug,
        "title": product.title,
        "merchant_name": product.merchant_name,
        "aisle": product.aisle,
        "price_xof": product.price_xof,
        "available": product.availability == SelectionProduct.Availability.AVAILABLE,
        "photo": asset_payload(photo.media) if photo else None,
        "group": group_payload(product),
    }


class SelectionProductSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    slug = serializers.CharField()
    title = serializers.CharField()
    merchant_name = serializers.CharField()
    aisle = serializers.ChoiceField(choices=Aisle.choices)
    price_xof = serializers.IntegerField()
    available = serializers.BooleanField()
    photo = MediaSerializer(allow_null=True)
    group = SelectionGroupSerializer(allow_null=True)


class SelectionProductListSerializer(serializers.Serializer):
    results = SelectionProductSummarySerializer(many=True)
    grouped = SelectionEstimateSerializer()
    express = SelectionEstimateSerializer()


def product_detail(product: SelectionProduct) -> dict:
    group = group_payload(product)
    after = None
    if group:
        after = selectors.open_group(product).ends_at.date()
    return {
        **product_summary(product),
        "description": product.description,
        "category": {
            "key": product.category.key,
            "name": product.category.name,
            "air_restricted": product.category.air_restricted,
        },
        "express_price_xof": product.express_price_xof,
        "options": [str(o) for o in product.options or []],
        "photos": [asset_payload(p.media) for p in product.photos.all()],
        "estimates": {
            "grouped": _estimate(ShippingMode.GROUPED),
            "express": _estimate(ShippingMode.EXPRESS),
            "group": _estimate(ShippingMode.GROUPED, after=after) if after else None,
        },
    }


class SelectionEstimatesSerializer(serializers.Serializer):
    grouped = SelectionEstimateSerializer()
    express = SelectionEstimateSerializer()
    group = SelectionEstimateSerializer(allow_null=True)


class SelectionProductDetailSerializer(SelectionProductSummarySerializer):
    description = serializers.CharField(allow_blank=True)
    category = SelectionCategorySerializer()
    express_price_xof = serializers.IntegerField(allow_null=True)
    options = serializers.ListField(child=serializers.CharField())
    photos = MediaSerializer(many=True)
    estimates = SelectionEstimatesSerializer()


class SelectionPickupPointSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    city = serializers.CharField()
    address = serializers.CharField()
    landmarks = serializers.CharField(allow_blank=True)
    hours = serializers.CharField(allow_blank=True)


def point_payload(point) -> dict:
    return {
        "id": str(point.pk),
        "name": point.name,
        "city": point.city,
        "address": point.address,
        "landmarks": point.landmarks,
        "hours": point.hours,
    }


class SelectionOrderInputSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    shipping_mode = serializers.ChoiceField(choices=ShippingMode.choices)
    pickup_point_id = serializers.UUIDField()
    option = serializers.CharField(required=False, allow_blank=True, max_length=60)
    quantity = serializers.IntegerField(required=False, default=1)
    group = serializers.BooleanField(required=False, default=False)
    voucher = serializers.CharField(required=False, allow_blank=True, default="", max_length=16)


def order_payload(order: SelectionOrder, viewer, *, with_payment: bool = True) -> dict:
    O = SelectionOrder.Status  # noqa: E741
    payment = order.payment
    photo = None
    if order.product_id:
        first = next(iter(order.product.photos.all()), None)
        photo = asset_payload(first.media) if first else None
    elif order.special_request_id and order.special_request.photo_id:
        photo = asset_payload(order.special_request.photo)
    group = order.group_buy
    return {
        "id": str(order.pk),
        "reference": order.reference,
        "status": order.status,
        "title": order.title,
        "option": order.option,
        "quantity": order.quantity,
        "unit_price_xof": order.unit_price_xof,
        "total_xof": order.total_xof,
        "discount_xof": order.discount_xof,
        "shipping_mode": order.shipping_mode,
        "photo": photo,
        "pickup_point": point_payload(order.pickup_point),
        "estimate_from": _iso(order.estimate_from),
        "estimate_to": _iso(order.estimate_to),
        "carrier": payment.carrier,
        "tracking_number": payment.tracking_number,
        "created_at": _iso(order.created_at),
        "ordered_at": _iso(order.ordered_at),
        "received_at": _iso(order.received_at),
        "shipped_at": _iso(order.shipped_at),
        "arrived_at": _iso(order.arrived_at),
        "completed_at": _iso(order.completed_at),
        "group": {
            "target": group.target_quantity,
            "count": selectors.group_count(group),
            "ends_at": _iso(group.ends_at),
            "status": group.status,
        }
        if group
        else None,
        "payment": payment_payload(payment, viewer) if with_payment else None,
        "can": {
            "pay": order.status == O.PENDING_PAYMENT and payment.status == "pending_payment",
            "cancel": order.status in (O.TO_ORDER, O.WAITING_GROUP),
        },
    }


class SelectionOrderGroupSerializer(serializers.Serializer):
    target = serializers.IntegerField()
    count = serializers.IntegerField()
    ends_at = serializers.DateTimeField()
    status = serializers.CharField()


class SelectionOrderAbilitiesSerializer(serializers.Serializer):
    pay = serializers.BooleanField()
    cancel = serializers.BooleanField()


class SelectionOrderSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    reference = serializers.CharField()
    status = serializers.ChoiceField(choices=SelectionOrder.Status.choices)
    title = serializers.CharField()
    option = serializers.CharField(allow_blank=True)
    quantity = serializers.IntegerField()
    unit_price_xof = serializers.IntegerField()
    total_xof = serializers.IntegerField()
    discount_xof = serializers.IntegerField()
    shipping_mode = serializers.ChoiceField(choices=ShippingMode.choices)
    photo = MediaSerializer(allow_null=True)
    pickup_point = SelectionPickupPointSerializer()
    estimate_from = serializers.DateField(allow_null=True)
    estimate_to = serializers.DateField(allow_null=True)
    carrier = serializers.CharField(allow_blank=True)
    tracking_number = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()
    ordered_at = serializers.DateTimeField(allow_null=True)
    received_at = serializers.DateTimeField(allow_null=True)
    shipped_at = serializers.DateTimeField(allow_null=True)
    arrived_at = serializers.DateTimeField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    group = SelectionOrderGroupSerializer(allow_null=True)
    payment = PaymentSerializer(allow_null=True)
    can = SelectionOrderAbilitiesSerializer()


class SelectionOrderListSerializer(serializers.Serializer):
    results = SelectionOrderSerializer(many=True)


class SelectionRequestInputSerializer(serializers.Serializer):
    link = serializers.CharField(required=False, allow_blank=True, max_length=500)
    photo = serializers.UUIDField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class SelectionQuoteOrderSerializer(serializers.Serializer):
    shipping_mode = serializers.ChoiceField(choices=ShippingMode.choices)
    pickup_point_id = serializers.UUIDField()


def request_payload(request: SpecialRequest) -> dict:
    quoted = request.status in (SpecialRequest.Status.QUOTED, SpecialRequest.Status.ORDERED)
    grouped, express = services.quote_prices(request) if quoted else (None, None)
    order = getattr(request, "order", None) if hasattr(request, "order") else None
    return {
        "id": str(request.pk),
        "status": request.status,
        "link": request.link,
        "photo": asset_payload(request.photo),
        "note": request.note,
        "created_at": _iso(request.created_at),
        "title": request.title if quoted else "",
        "price_xof": grouped,
        "express_price_xof": express,
        "answer": request.answer,
        "valid_until": _iso(request.valid_until) if quoted else None,
        "estimates": {
            "grouped": _estimate(ShippingMode.GROUPED),
            "express": _estimate(ShippingMode.EXPRESS),
            "group": None,
        },
        "order_id": str(order.pk) if order else None,
    }


class SelectionRequestSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=SpecialRequest.Status.choices)
    link = serializers.CharField(allow_blank=True)
    photo = MediaSerializer(allow_null=True)
    note = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()
    title = serializers.CharField(allow_blank=True)
    price_xof = serializers.IntegerField(allow_null=True)
    express_price_xof = serializers.IntegerField(allow_null=True)
    answer = serializers.CharField(allow_blank=True)
    valid_until = serializers.DateTimeField(allow_null=True)
    estimates = SelectionEstimatesSerializer()
    order_id = serializers.UUIDField(allow_null=True)
