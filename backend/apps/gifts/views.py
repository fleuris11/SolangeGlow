from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttling import SettingRateThrottle
from apps.accounts.views_base import OptionalAuthView
from apps.booking import selectors as booking_selectors
from apps.booking import serializers as booking_serializers

from . import errors, selectors, services
from .models import Gift
from .serializers import (
    GiftBookSerializer,
    GiftCheckoutSerializer,
    GiftCreateSerializer,
    GiftIdeasSerializer,
    GiftOptionsSerializer,
    GiftPaidSerializer,
    GiftPaySerializer,
    GiftPhotoUploadSerializer,
    GiftProofSerializer,
    GiftQuoteQuerySerializer,
    GiftQuoteSerializer,
    GiftReceivedSerializer,
    GiftReceiveSerializer,
    GiftReceptionSerializer,
    GiftSentSerializer,
    GlowCardCheckSerializer,
    GlowCardSerializer,
)

TAGS = ["gifts"]


class GiftView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "gifts"


class PublicGiftView(OptionalAuthView):
    throttle_scope = "gifts"


def _quote_args(values: dict) -> dict:
    return {
        "service_id": values.get("service"),
        "variant_id": values.get("variant"),
        "delivery_mode": values.get("delivery_mode") or "",
        "zone_id": values.get("zone"),
        "selection_product_id": values.get("selection_product"),
        "option": values.get("option") or "",
        "amount_minor": values.get("amount_minor"),
    }


def _viewer(request):
    return request.user if request.user.is_authenticated else None


class IdeasView(PublicGiftView):
    @extend_schema(tags=TAGS, responses=GiftIdeasSerializer)
    def get(self, request):
        return Response(GiftIdeasSerializer(selectors.ideas_payload()).data)


class QuoteView(PublicGiftView):
    @extend_schema(tags=TAGS, parameters=[GiftQuoteQuerySerializer], responses=GiftQuoteSerializer)
    def get(self, request):
        query = GiftQuoteQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        values = query.validated_data
        found = services.quote(values["kind"], **_quote_args(values))
        return Response(GiftQuoteSerializer(selectors.quote_payload(found)).data)


class ProductOptionsView(PublicGiftView):
    @extend_schema(tags=TAGS, operation_id="gifts_product_options", responses=GiftOptionsSerializer)
    def get(self, request, variant_id):
        return Response(GiftOptionsSerializer(selectors.product_options(variant_id)).data)


class SentView(GiftView):
    @extend_schema(tags=TAGS, responses=GiftSentSerializer(many=True))
    def get(self, request):
        rows = [selectors.for_giver(g) for g in selectors.sent_by(request.user)[:100]]
        return Response(GiftSentSerializer(rows, many=True).data)

    @extend_schema(
        tags=TAGS,
        operation_id="gifts_offer",
        request=GiftCreateSerializer,
        responses=GiftCheckoutSerializer,
    )
    def post(self, request):
        data = GiftCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        found = services.quote(values["kind"], **_quote_args(values))
        gift = services.offer(
            request.user,
            found,
            recipient_name=values["recipient_name"],
            recipient_phone=values["recipient_phone"],
            recipient_email=values["recipient_email"],
            language=values["language"],
            occasion=values["occasion"],
            message=values["message"],
            message_media_id=values.get("message_media_id"),
            send_at=values.get("send_at"),
            from_name=values["from_name"],
        )
        payment = services.start_payment(gift, request.user)
        gift.refresh_from_db()
        return Response(
            GiftCheckoutSerializer(
                {"gift": selectors.for_giver(gift), "checkout_url": payment.checkout_url}
            ).data,
            status=201,
        )


def _mine(request, gift_id) -> Gift:
    return get_object_or_404(Gift, pk=gift_id, giver=request.user)


class SentGiftView(GiftView):
    @extend_schema(tags=TAGS, operation_id="gifts_sent_detail", responses=GiftSentSerializer)
    def get(self, request, gift_id):
        return Response(GiftSentSerializer(selectors.for_giver(_mine(request, gift_id))).data)


class PayView(GiftView):
    @extend_schema(
        tags=TAGS, operation_id="gifts_pay_again", request=None, responses=GiftCheckoutSerializer
    )
    def post(self, request, gift_id):
        gift = _mine(request, gift_id)
        payment = services.start_payment(gift, request.user)
        return Response(
            GiftCheckoutSerializer(
                {"gift": selectors.for_giver(gift), "checkout_url": payment.checkout_url}
            ).data
        )


class CancelView(GiftView):
    @extend_schema(
        tags=TAGS, operation_id="gifts_cancel", request=None, responses=GiftSentSerializer
    )
    def post(self, request, gift_id):
        gift = services.cancel(_mine(request, gift_id), actor=request.user)
        return Response(GiftSentSerializer(selectors.for_giver(gift)).data)


class ResendView(GiftView):
    @extend_schema(
        tags=TAGS, operation_id="gifts_resend", request=None, responses=GiftSentSerializer
    )
    def post(self, request, gift_id):
        gift = services.resend(_mine(request, gift_id), actor=request.user)
        return Response(GiftSentSerializer(selectors.for_giver(gift)).data)


class ReceivedView(GiftView):
    @extend_schema(tags=TAGS, responses=GiftReceivedSerializer(many=True))
    def get(self, request):
        rows = [selectors.received_payload(g) for g in selectors.received_by(request.user)[:100]]
        return Response(GiftReceivedSerializer(rows, many=True).data)


class CardPayView(GiftView):
    throttle_scope = "gift_code"

    @extend_schema(
        tags=TAGS,
        operation_id="gifts_pay_with_card",
        request=GiftPaySerializer,
        responses=GiftPaidSerializer,
    )
    def post(self, request):
        data = GiftPaySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        card = services.pay_with_card(
            values["code"],
            user=request.user,
            payment_id=values.get("payment_id"),
            group_id=values.get("group_id"),
        )
        return Response(
            GiftPaidSerializer(
                {"balance": {"amount_minor": card.balance_minor, "currency": card.currency}}
            ).data
        )


class CardCheckView(GiftView):
    throttle_scope = "gift_code"

    @extend_schema(
        tags=TAGS,
        operation_id="gifts_card_check",
        request=GlowCardCheckSerializer,
        responses=GlowCardSerializer,
    )
    def post(self, request):
        data = GlowCardCheckSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        card = services.card_by_code(data.validated_data["code"])
        if card is None or not services.common.usable(card):
            raise errors.GiftNotFound()
        return Response(
            GlowCardSerializer(
                {
                    "balance": {"amount_minor": card.balance_minor, "currency": card.currency},
                    "expires_on": card.expires_on,
                    "from_name": card.from_name,
                }
            ).data
        )


# --- The page of the gift (secret link, with or without an account) ------------------------------


def _reception(request, gift: Gift) -> Response:
    gift = services.by_token(gift.token)
    return Response(GiftReceptionSerializer(selectors.reception(gift, _viewer(request))).data)


class ReceptionView(PublicGiftView):
    @extend_schema(tags=TAGS, operation_id="gifts_open", responses=GiftReceptionSerializer)
    def get(self, request, token):
        gift = services.open_gift(services.by_token(token), _viewer(request))
        return _reception(request, gift)


class ClaimView(GiftView):
    @extend_schema(
        tags=TAGS, operation_id="gifts_claim", request=None, responses=GiftReceptionSerializer
    )
    def post(self, request, token):
        gift = services.claim(services.by_token(token), request.user)
        return _reception(request, gift)


class BookView(PublicGiftView):
    @extend_schema(
        tags=TAGS,
        operation_id="gifts_book",
        request=GiftBookSerializer,
        responses={201: booking_serializers.BookedSerializer},
    )
    def post(self, request, token):
        data = GiftBookSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        appointment = services.book(
            services.by_token(token),
            values["start"],
            viewer=_viewer(request),
            staff_id=values.get("staff_id"),
            guest_name=values["guest_name"],
            guest_phone=values["guest_phone"],
            note=values["note"],
        )
        fresh = booking_selectors.appointment_by_id(appointment.pk)
        return Response(
            booking_serializers.booked_payload(fresh, guest=fresh.client_id is None), status=201
        )


class ReceiveView(PublicGiftView):
    @extend_schema(
        tags=TAGS,
        operation_id="gifts_receive",
        request=GiftReceiveSerializer,
        responses=GiftReceptionSerializer,
    )
    def post(self, request, token):
        data = GiftReceiveSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        gift = services.by_token(token)
        services.receive(gift, viewer=_viewer(request), **data.validated_data)
        return _reception(request, gift)


class AsCardView(PublicGiftView):
    @extend_schema(
        tags=TAGS, operation_id="gifts_as_card", request=None, responses=GiftReceptionSerializer
    )
    def post(self, request, token):
        gift = services.as_card(services.by_token(token), viewer=_viewer(request))
        return _reception(request, gift)


class PhotoView(PublicGiftView):
    parser_classes = [MultiPartParser]
    throttle_scope = "media_upload"

    @extend_schema(
        tags=TAGS,
        operation_id="gifts_add_photo",
        request=GiftPhotoUploadSerializer,
        responses=GiftReceptionSerializer,
    )
    def post(self, request, token):
        data = GiftPhotoUploadSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        gift = services.by_token(token)
        services.add_photo(gift, data.validated_data["file"], viewer=_viewer(request))
        return _reception(request, gift)


class ProofView(PublicGiftView):
    @extend_schema(
        tags=TAGS,
        operation_id="gifts_answer_proof",
        request=GiftProofSerializer,
        responses=GiftReceptionSerializer,
    )
    def post(self, request, token):
        data = GiftProofSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        gift = services.by_token(token)
        services.answer(
            gift,
            data.validated_data.get("media_id"),
            send=data.validated_data["send"],
            viewer=_viewer(request),
        )
        return _reception(request, gift)
