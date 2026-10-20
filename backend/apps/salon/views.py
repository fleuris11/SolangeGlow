from __future__ import annotations

import datetime
import uuid

from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttling import SettingRateThrottle
from apps.accounts.views_base import OptionalAuthView
from apps.booking import selectors as booking_selectors
from apps.booking.models import Appointment, ClientRecord
from apps.glowpro import selectors as glowpro
from apps.glowpro.models import Feature
from apps.glowpro.serializers import CheckoutUrlSerializer
from apps.invoicing.views import DocumentSerializer, document_payload
from apps.pros.models import ProProfile, Service

from . import errors, terminal
from . import serializers as s
from .models import (
    Campaign,
    ClientPackage,
    GiftCard,
    Installment,
    MarketingConsent,
    OnSitePayment,
    Package,
    StockItem,
)
from .services import campaigns, common, documents, giftcards, onsite, packages, stock


class SalonView(APIView):
    """Pages of the salon. `members`: collaborators too (payments, gift cards at the desk)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "salon"
    members = False

    def get_throttles(self):
        return super().get_throttles() if self.request.method != "GET" else []

    def pro(self, request) -> ProProfile:
        pro, staff_ids = booking_selectors.agenda_access(request.user)
        if pro is None or (staff_ids is not None and not self.members):
            raise errors.NotFound()
        return pro


def _published(slug) -> ProProfile:
    pro = ProProfile.objects.filter(slug=slug, status=ProProfile.Status.PUBLISHED).first()
    if pro is None:
        raise errors.NotFound()
    return pro


# --- Packages -----------------------------------------------------------------------------------


class PackagesView(SalonView):
    @extend_schema(tags=["salon"], responses=s.PackageSerializer(many=True))
    def get(self, request):
        rows = Package.objects.filter(pro=self.pro(request)).select_related("service")
        return Response([s.package_payload(p) for p in rows.order_by("name")])

    @extend_schema(
        tags=["salon"], request=s.PackageInputSerializer, responses={201: s.PackageSerializer}
    )
    def post(self, request):
        data = s.PackageInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        package = packages.save_package(self.pro(request), **data.validated_data)
        return Response(s.package_payload(package), status=status.HTTP_201_CREATED)


class PackageView(SalonView):
    @extend_schema(tags=["salon"], request=s.PackageInputSerializer, responses=s.PackageSerializer)
    def put(self, request, package_id):
        data = s.PackageInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        package = packages.save_package(
            self.pro(request), package_id=package_id, **data.validated_data
        )
        return Response(s.package_payload(package))


class SessionUseView(SalonView):
    members = True

    @extend_schema(tags=["salon"], request=None, responses=s.SoldPackageSerializer)
    def post(self, request, sold_id):
        sold = ClientPackage.objects.filter(pk=sold_id, pro=self.pro(request)).first()
        if sold is None:
            raise errors.NotFound()
        sold = packages.use_session(sold, actor=request.user)
        return Response(s.sold_payload(sold))


class InstallmentRecordView(SalonView):
    members = True

    @extend_schema(
        tags=["salon"], request=s.MethodInputSerializer, responses=s.InstallmentSerializer
    )
    def post(self, request, installment_id):
        data = s.MethodInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        installment = Installment.objects.filter(
            pk=installment_id, plan__pro=self.pro(request)
        ).first()
        if installment is None:
            raise errors.NotFound()
        installment = packages.record_on_site(
            installment, method=data.validated_data["method"], actor=request.user
        )
        return Response(s.installment_payload(installment))


# --- The complete client file -------------------------------------------------------------------


class ClientFileView(SalonView):
    def answer(self, pro, record) -> Response:
        premium = glowpro.has_feature(pro, Feature.CLIENT_FILE)
        record = ClientRecord.objects.prefetch_related("consents").get(pk=record.pk)
        return Response(s.client_file_payload(record, premium=premium))

    @extend_schema(tags=["salon"], responses=s.ClientFileSerializer)
    def get(self, request, record_id):
        pro = self.pro(request)
        return self.answer(pro, common.record_of(pro, record_id))

    @extend_schema(
        tags=["salon"], request=s.ClientFileInputSerializer, responses=s.ClientFileSerializer
    )
    def patch(self, request, record_id):
        pro = self.pro(request)
        record = common.record_of(pro, record_id)
        data = s.ClientFileInputSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        if "email" in values:
            record.email = values["email"]
        if "birthday_day" in values or "birthday_month" in values:
            day, month = values.get("birthday_day"), values.get("birthday_month")
            if bool(day) != bool(month):
                raise errors.InvalidPayment()
            record.birthday_day, record.birthday_month = day, month
        record.save()
        for channel in ("email", "whatsapp"):
            key = f"{channel}_consent"
            if key in values:
                campaigns.set_consent(
                    record, channel, values[key], source=MarketingConsent.Source.PRO
                )
        return self.answer(pro, record)


class SellPackageView(SalonView):
    @extend_schema(
        tags=["salon"],
        request=s.SellPackageInputSerializer,
        responses={201: s.SoldPackageSerializer},
    )
    def post(self, request, record_id):
        pro = self.pro(request)
        data = s.SellPackageInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        sold = packages.sell_on_site(
            pro,
            data.validated_data["package_id"],
            common.record_of(pro, record_id),
            installments=data.validated_data["installments"],
            method=data.validated_data["method"],
            actor=request.user,
        )
        return Response(s.sold_payload(sold), status=status.HTTP_201_CREATED)


# --- Gift cards ---------------------------------------------------------------------------------


class GiftCardsView(SalonView):
    members = True

    @extend_schema(
        tags=["salon"],
        parameters=[OpenApiParameter("q", str, required=False)],
        responses=s.GiftCardSerializer(many=True),
    )
    def get(self, request):
        rows = GiftCard.objects.filter(pro=self.pro(request)).exclude(
            status=GiftCard.Status.WAITING
        )
        q = (request.query_params.get("q") or "").strip().upper()
        if q:
            rows = rows.filter(Q(code__icontains=q) | Q(recipient_name__icontains=q))
        return Response([s.gift_card_payload(c) for c in rows.select_related("pro")[:100]])

    @extend_schema(
        tags=["salon"], request=s.SellGiftCardInputSerializer, responses={201: s.GiftCardSerializer}
    )
    def post(self, request):
        data = s.SellGiftCardInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        card = giftcards.sell_on_site(self.pro(request), actor=request.user, **data.validated_data)
        return Response(s.gift_card_payload(card), status=status.HTTP_201_CREATED)


class GiftCardCheckView(SalonView):
    members = True

    @extend_schema(
        tags=["salon"],
        parameters=[OpenApiParameter("code", str, required=True)],
        responses=s.GiftCardCheckSerializer,
    )
    def get(self, request):
        from django.db import transaction

        with transaction.atomic():
            card = giftcards.find(self.pro(request), request.query_params.get("code", ""))
        return Response(
            {
                "code": card.code,
                "balance_minor": card.balance_minor,
                "currency": card.currency,
                "expires_on": card.expires_on.isoformat(),
            }
        )


class GiftCardRedeemView(SalonView):
    members = True

    @extend_schema(tags=["salon"], request=s.RedeemInputSerializer, responses=s.GiftCardSerializer)
    def post(self, request):
        pro = self.pro(request)
        data = s.RedeemInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        appointment = None
        if values.get("appointment_id"):
            appointment = Appointment.objects.filter(pk=values["appointment_id"], pro=pro).first()
        card = giftcards.redeem(
            pro, values["code"], values["amount_minor"], actor=request.user, appointment=appointment
        )
        return Response(s.gift_card_payload(card))


# --- Stock --------------------------------------------------------------------------------------


class StockView(SalonView):
    @extend_schema(
        tags=["salon"],
        parameters=[OpenApiParameter("low", bool, required=False)],
        responses=s.StockItemSerializer(many=True),
    )
    def get(self, request):
        pro = self.pro(request)
        glowpro.require(pro, Feature.STOCK)
        rows = StockItem.objects.filter(pro=pro, is_active=True).select_related("variant")
        items = [s.item_payload(i) for i in rows]
        if request.query_params.get("low") in ("1", "true"):
            items = [i for i in items if i["low"]]
        return Response(sorted(items, key=lambda i: (not i["low"], i["name"].lower())))

    @extend_schema(
        tags=["salon"], request=s.StockItemInputSerializer, responses={201: s.StockItemSerializer}
    )
    def post(self, request):
        data = s.StockItemInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        item = stock.save_item(self.pro(request), actor=request.user, **data.validated_data)
        return Response(s.item_payload(item), status=status.HTTP_201_CREATED)


def _item(pro, item_id) -> StockItem:
    item = StockItem.objects.filter(pk=item_id, pro=pro).select_related("variant").first()
    if item is None:
        raise errors.NotFound()
    return item


class StockItemView(SalonView):
    @extend_schema(
        tags=["salon"],
        operation_id="salon_stock_movements",
        responses=s.MovementSerializer(many=True),
    )
    def get(self, request, item_id):
        item = _item(self.pro(request), item_id)
        return Response([s.movement_payload(m) for m in item.movements.all()[:50]])

    @extend_schema(
        tags=["salon"], request=s.StockItemInputSerializer, responses=s.StockItemSerializer
    )
    def put(self, request, item_id):
        pro = self.pro(request)
        data = s.StockItemInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = {k: v for k, v in data.validated_data.items() if k != "quantity"}
        item = stock.save_item(pro, item_id=_item(pro, item_id).pk, actor=request.user, **values)
        return Response(s.item_payload(item))

    @extend_schema(tags=["salon"], request=None, responses={204: None})
    def delete(self, request, item_id):
        item = _item(self.pro(request), item_id)
        item.is_active = False
        item.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class StockMoveView(SalonView):
    @extend_schema(
        tags=["salon"], request=s.StockMoveInputSerializer, responses=s.StockItemSerializer
    )
    def post(self, request, item_id):
        pro = self.pro(request)
        glowpro.require(pro, Feature.STOCK)
        data = s.StockMoveInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        sign = 1 if values["kind"] == "in" else -1
        item = _item(pro, item_id)
        stock.move(
            item,
            sign * values["quantity"],
            values["kind"],
            actor=request.user,
            note=values.get("note", ""),
        )
        return Response(s.item_payload(_item(pro, item_id)))


class StockCountView(SalonView):
    @extend_schema(tags=["salon"], request=s.CountInputSerializer, responses=s.StockItemSerializer)
    def post(self, request, item_id):
        pro = self.pro(request)
        glowpro.require(pro, Feature.STOCK)
        data = s.CountInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        stock.count(_item(pro, item_id), data.validated_data["counted"], actor=request.user)
        return Response(s.item_payload(_item(pro, item_id)))


class StockBarcodeView(SalonView):
    @extend_schema(tags=["salon"], responses=s.StockItemSerializer)
    def get(self, request, ean):
        pro = self.pro(request)
        glowpro.require(pro, Feature.STOCK)
        item = stock.find_by_ean(pro, ean)
        if item is None:
            raise errors.NotFound()
        return Response(s.item_payload(item))


class ConsumptionView(SalonView):
    @extend_schema(tags=["salon"], responses=s.ConsumptionRowSerializer(many=True))
    def get(self, request, service_id):
        pro = self.pro(request)
        service = Service.objects.filter(pk=service_id, pro=pro).first()
        if service is None:
            raise errors.NotFound()
        return Response(
            [
                {"item_id": str(c.item_id), "quantity": c.quantity}
                for c in service.consumptions.all()
            ]
        )

    @extend_schema(
        tags=["salon"],
        request=s.ConsumptionInputSerializer,
        responses=s.ConsumptionRowSerializer(many=True),
    )
    def put(self, request, service_id):
        data = s.ConsumptionInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        service = stock.set_consumption(self.pro(request), service_id, data.validated_data["rows"])
        return Response(
            [
                {"item_id": str(c.item_id), "quantity": c.quantity}
                for c in service.consumptions.all()
            ]
        )


# --- Payments at the salon and documents -------------------------------------------------------


class PaymentMethodsView(SalonView):
    members = True

    @extend_schema(tags=["salon"], responses=s.PaymentMethodsSerializer)
    def get(self, request):
        pro = self.pro(request)
        return Response(
            {
                "methods": onsite.methods_for(pro),
                "terminal_configured": terminal.is_configured(
                    pro.country.code if pro.country_id else ""
                ),
                "certified_till": False,
                "currency": pro.currency or "XOF",
            }
        )


class OnSitePaymentsView(SalonView):
    members = True

    @extend_schema(
        tags=["salon"],
        parameters=[
            OpenApiParameter("day", str, required=False),
            OpenApiParameter("appointment", str, required=False),
        ],
        responses=s.OnSitePaymentSerializer(many=True),
    )
    def get(self, request):
        pro = self.pro(request)
        rows = OnSitePayment.objects.filter(pro=pro).select_related("record")
        appointment = request.query_params.get("appointment")
        if appointment:
            try:
                rows = rows.filter(appointment_id=uuid.UUID(appointment))
            except ValueError:
                rows = rows.none()
        day = request.query_params.get("day")
        if day:
            try:
                rows = rows.filter(created_at__date=datetime.date.fromisoformat(day))
            except ValueError:
                rows = rows.none()
        return Response([s.on_site_payload(p) for p in rows[:200]])

    @extend_schema(
        tags=["salon"],
        request=s.OnSitePaymentInputSerializer,
        responses={201: s.OnSitePaymentSerializer},
    )
    def post(self, request):
        pro = self.pro(request)
        data = s.OnSitePaymentInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        appointment = None
        if values.get("appointment_id"):
            appointment = Appointment.objects.filter(pk=values["appointment_id"], pro=pro).first()
            if appointment is None:
                raise errors.NotFound()
        client_record = (
            common.record_of(pro, values["record_id"]) if values.get("record_id") else None
        )
        payment = onsite.record_payment(
            pro,
            amount_minor=values["amount_minor"],
            method=values["method"],
            actor=request.user,
            label=values.get("label", ""),
            appointment=appointment,
            client_record=client_record,
            reference=values.get("reference", ""),
        )
        return Response(s.on_site_payload(payment), status=status.HTTP_201_CREATED)


def _on_site(pro, payment_id) -> OnSitePayment:
    payment = OnSitePayment.objects.filter(pk=payment_id, pro=pro).select_related("record").first()
    if payment is None:
        raise errors.NotFound()
    return payment


class OnSiteCancelView(SalonView):
    @extend_schema(
        tags=["salon"], request=s.ReasonInputSerializer, responses=s.OnSitePaymentSerializer
    )
    def post(self, request, payment_id):
        pro = self.pro(request)
        data = s.ReasonInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        payment = onsite.cancel_payment(
            _on_site(pro, payment_id), actor=request.user, reason=data.validated_data["reason"]
        )
        return Response(s.on_site_payload(payment))


class OnSiteReceiptView(SalonView):
    members = True

    @extend_schema(tags=["salon"], request=None, responses=DocumentSerializer)
    def post(self, request, payment_id):
        receipt = documents.for_on_site(_on_site(self.pro(request), payment_id))
        return Response(document_payload(receipt))


class AppointmentInvoiceView(SalonView):
    members = True

    @extend_schema(tags=["salon"], request=None, responses=DocumentSerializer)
    def post(self, request, appointment_id):
        appointment = Appointment.objects.filter(pk=appointment_id, pro=self.pro(request)).first()
        if appointment is None:
            raise errors.NotFound()
        return Response(document_payload(documents.for_appointment(appointment)))


# --- Campaigns ----------------------------------------------------------------------------------


class CampaignsView(SalonView):
    @extend_schema(tags=["salon"], responses=s.CampaignSerializer(many=True))
    def get(self, request):
        pro = self.pro(request)
        glowpro.require(pro, Feature.CAMPAIGNS)
        return Response([s.campaign_payload(c) for c in Campaign.objects.filter(pro=pro)[:50]])

    @extend_schema(
        tags=["salon"], request=s.CampaignInputSerializer, responses={201: s.CampaignSerializer}
    )
    def post(self, request):
        data = s.CampaignInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        campaign = campaigns.save_campaign(self.pro(request), **data.validated_data)
        return Response(s.campaign_payload(campaign), status=status.HTTP_201_CREATED)


def _campaign(pro, campaign_id) -> Campaign:
    found = Campaign.objects.filter(pk=campaign_id, pro=pro).select_related("pro").first()
    if found is None:
        raise errors.NotFound()
    return found


class CampaignView(SalonView):
    @extend_schema(tags=["salon"], responses=s.AudienceSerializer)
    def get(self, request, campaign_id):
        """Who would receive it now (before sending)."""
        pro = self.pro(request)
        glowpro.require(pro, Feature.CAMPAIGNS)
        chosen, left_out = campaigns.audience(_campaign(pro, campaign_id))
        start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return Response(
            {
                "recipients": len(chosen),
                "without_consent": left_out,
                "limit": glowpro.limit(pro, "campaigns_per_month"),
                "sent_this_month": Campaign.objects.filter(
                    pro=pro, status="sent", sent_at__gte=start
                ).count(),
            }
        )

    @extend_schema(
        tags=["salon"], request=s.CampaignInputSerializer, responses=s.CampaignSerializer
    )
    def put(self, request, campaign_id):
        pro = self.pro(request)
        data = s.CampaignInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        campaign = campaigns.save_campaign(
            pro, campaign_id=_campaign(pro, campaign_id).pk, **data.validated_data
        )
        return Response(s.campaign_payload(campaign))


class CampaignSendView(SalonView):
    @extend_schema(tags=["salon"], request=None, responses=s.CampaignSerializer)
    def post(self, request, campaign_id):
        pro = self.pro(request)
        campaign = campaigns.send(_campaign(pro, campaign_id), actor=request.user)
        return Response(s.campaign_payload(campaign))


class UnsubscribeView(APIView):
    """The link at the bottom of each message: no account needed."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "widget"

    @extend_schema(tags=["salon"], responses=s.UnsubscribeSerializer)
    def get(self, request, token):
        found, channel = campaigns.read_token(token)
        consent = found.consents.filter(channel=channel).first()
        return Response(
            {
                "pro_name": found.pro.display_name,
                "channel": channel,
                "unsubscribed": consent is not None and not consent.granted,
            }
        )

    @extend_schema(tags=["salon"], request=None, responses=s.UnsubscribeSerializer)
    def post(self, request, token):
        found, channel = campaigns.unsubscribe(token)
        return Response(
            {"pro_name": found.pro.display_name, "channel": channel, "unsubscribed": True}
        )


# --- For clients: packages and gift cards of a salon --------------------------------------------


class PublicOffersView(OptionalAuthView):
    """Packages and gift cards a client can buy on a showcase."""

    @extend_schema(tags=["salon"], responses=s.PublicPackagesSerializer)
    def get(self, request, slug):
        pro = _published(slug)
        rows = []
        if glowpro.has_feature(pro, Feature.CLIENT_FILE):
            rows = Package.objects.filter(pro=pro, is_active=True).select_related("service")
        return Response(
            {"packages": [s.package_payload(p) for p in rows], "gift_cards": giftcards.offer(pro)}
        )


class ClientView(APIView):
    """What a client does (buy a package or a gift card, pay an installment)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "salon"

    def get_throttles(self):
        return super().get_throttles() if self.request.method != "GET" else []


class BuyPackageView(ClientView):
    @extend_schema(
        tags=["salon"], request=s.BuyPackageInputSerializer, responses=CheckoutUrlSerializer
    )
    def post(self, request, slug, package_id):
        data = s.BuyPackageInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        payment = packages.buy_online(
            request.user,
            _published(slug),
            package_id,
            installments=data.validated_data["installments"],
        )
        return Response({"checkout_url": payment.checkout_url})


class BuyGiftCardView(ClientView):
    @extend_schema(
        tags=["salon"], request=s.BuyGiftCardInputSerializer, responses=CheckoutUrlSerializer
    )
    def post(self, request, slug):
        data = s.BuyGiftCardInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        _card, payment = giftcards.buy_online(request.user, _published(slug), **data.validated_data)
        return Response({"checkout_url": payment.checkout_url})


class PayInstallmentView(ClientView):
    @extend_schema(tags=["salon"], request=None, responses=CheckoutUrlSerializer)
    def post(self, request, installment_id):
        installment = Installment.objects.filter(
            pk=installment_id, plan__record__client=request.user
        ).first()
        if installment is None:
            raise errors.NotFound()
        payment = packages.pay_online(installment, request.user)
        return Response({"checkout_url": payment.checkout_url})


class MyPackagesView(ClientView):
    @extend_schema(tags=["salon"], responses=s.ClientPackagesSerializer)
    def get(self, request):
        booking_selectors.claim_guest_appointments(request.user)
        sold = (
            ClientPackage.objects.filter(record__client=request.user)
            .exclude(status=ClientPackage.Status.CANCELLED)
            .select_related("package__service", "pro")
            .prefetch_related("installment_plan__installments")
        )
        cards = GiftCard.objects.filter(buyer=request.user).exclude(status=GiftCard.Status.WAITING)
        return Response(
            {
                "packages": [s.sold_payload(p) for p in sold],
                "gift_cards": [s.gift_card_payload(c) for c in cards.select_related("pro")],
            }
        )
