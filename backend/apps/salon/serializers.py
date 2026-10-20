"""What the web app gets from the salon management, and what it sends."""

from __future__ import annotations

from rest_framework import serializers

from apps.booking.models import ClientRecord

from .models import (
    Campaign,
    Channel,
    ClientPackage,
    GiftCard,
    Installment,
    OnSitePayment,
    Package,
    StockItem,
    StockMovement,
)
from .services import campaigns, common


def _iso(value):
    return value.isoformat() if value else None


# --- Packages -----------------------------------------------------------------------------------


def package_payload(package: Package) -> dict:
    return {
        "id": str(package.pk),
        "service_id": str(package.service_id),
        "service_name": package.service.name,
        "name": package.name,
        "sessions": package.sessions,
        "price_minor": package.price_minor,
        "currency": package.currency,
        "validity_days": package.validity_days,
        "max_installments": package.max_installments,
        "is_active": package.is_active,
    }


class PackageSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    service_id = serializers.UUIDField()
    service_name = serializers.CharField()
    name = serializers.CharField()
    sessions = serializers.IntegerField()
    price_minor = serializers.IntegerField()
    currency = serializers.CharField()
    validity_days = serializers.IntegerField()
    max_installments = serializers.IntegerField()
    is_active = serializers.BooleanField()


class PackageInputSerializer(serializers.Serializer):
    service_id = serializers.UUIDField()
    name = serializers.CharField(max_length=80)
    sessions = serializers.IntegerField(min_value=2, max_value=50)
    price_minor = serializers.IntegerField(min_value=1)
    validity_days = serializers.IntegerField(min_value=7, max_value=1095, required=False)
    max_installments = serializers.IntegerField(min_value=1, max_value=4, required=False)
    is_active = serializers.BooleanField(required=False)


def installment_payload(installment: Installment) -> dict:
    return {
        "id": str(installment.pk),
        "position": installment.position,
        "due_on": installment.due_on.isoformat(),
        "amount_minor": installment.amount_minor,
        "status": installment.status,
        "paid_at": _iso(installment.paid_at),
        "online": installment.payment_id is not None and installment.status == "paid",
    }


class InstallmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    position = serializers.IntegerField()
    due_on = serializers.DateField()
    amount_minor = serializers.IntegerField()
    status = serializers.ChoiceField(choices=Installment.Status.choices)
    paid_at = serializers.DateTimeField(allow_null=True)
    online = serializers.BooleanField()


def sold_payload(sold: ClientPackage) -> dict:
    plan = getattr(sold, "installment_plan", None)
    return {
        "id": str(sold.pk),
        "name": sold.package.name,
        "service_name": sold.package.service.name,
        "pro_name": sold.pro.display_name,
        "pro_slug": sold.pro.slug,
        "sessions_total": sold.sessions_total,
        "sessions_used": sold.sessions_used,
        "price_minor": sold.price_minor,
        "currency": sold.currency,
        "expires_on": sold.expires_on.isoformat(),
        "status": sold.status,
        "installments": [installment_payload(i) for i in plan.installments.all()] if plan else [],
    }


class SoldPackageSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    service_name = serializers.CharField()
    pro_name = serializers.CharField()
    pro_slug = serializers.CharField(allow_null=True)
    sessions_total = serializers.IntegerField()
    sessions_used = serializers.IntegerField()
    price_minor = serializers.IntegerField()
    currency = serializers.CharField()
    expires_on = serializers.DateField()
    status = serializers.ChoiceField(choices=ClientPackage.Status.choices)
    installments = InstallmentSerializer(many=True)


class SellPackageInputSerializer(serializers.Serializer):
    package_id = serializers.UUIDField()
    installments = serializers.IntegerField(min_value=1, max_value=4, default=1)
    method = serializers.ChoiceField(choices=OnSitePayment.Method.choices)


class BuyPackageInputSerializer(serializers.Serializer):
    installments = serializers.IntegerField(min_value=1, max_value=4, default=1)


class MethodInputSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=OnSitePayment.Method.choices)


# --- The complete client file -------------------------------------------------------------------


def client_file_payload(record: ClientRecord, *, premium: bool) -> dict:
    consents = {c.channel: c for c in record.consents.all()}
    birthday = common.birthday(record)
    return {
        "id": str(record.pk),
        "name": record.name,
        "email": record.email,
        "birthday_day": birthday[0] if birthday else None,
        "birthday_month": birthday[1] if birthday else None,
        "consents": [
            {
                "channel": channel,
                "granted": consents[channel].granted if channel in consents else False,
                "source": consents[channel].source if channel in consents else "",
                "changed_at": _iso(consents[channel].changed_at) if channel in consents else None,
            }
            for channel in Channel.values
        ],
        "packages": [
            sold_payload(p)
            for p in record.packages.select_related("package__service", "pro").prefetch_related(
                "installment_plan__installments"
            )
        ]
        if premium
        else [],
        "premium": premium,
    }


class ConsentSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=Channel.choices)
    granted = serializers.BooleanField()
    source = serializers.CharField(allow_blank=True)
    changed_at = serializers.DateTimeField(allow_null=True)


class ClientFileSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    email = serializers.CharField(allow_blank=True)
    birthday_day = serializers.IntegerField(allow_null=True)
    birthday_month = serializers.IntegerField(allow_null=True)
    consents = ConsentSerializer(many=True)
    packages = SoldPackageSerializer(many=True)
    premium = serializers.BooleanField()


class ClientFileInputSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    birthday_day = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, max_value=31
    )
    birthday_month = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, max_value=12
    )
    email_consent = serializers.BooleanField(required=False)
    whatsapp_consent = serializers.BooleanField(required=False)


# --- Gift cards ---------------------------------------------------------------------------------


def gift_card_payload(card: GiftCard) -> dict:
    return {
        "id": str(card.pk),
        "code": card.code,
        "amount_minor": card.amount_minor,
        "balance_minor": card.balance_minor,
        "currency": card.currency,
        "recipient_name": card.recipient_name,
        "from_name": card.from_name,
        "expires_on": card.expires_on.isoformat(),
        "status": card.status,
        "sold_on_site": card.sold_on_site,
        "pro_name": card.pro.display_name,
        "pro_slug": card.pro.slug,
        "created_at": _iso(card.created_at),
    }


class GiftCardSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    code = serializers.CharField()
    amount_minor = serializers.IntegerField()
    balance_minor = serializers.IntegerField()
    currency = serializers.CharField()
    recipient_name = serializers.CharField()
    from_name = serializers.CharField(allow_blank=True)
    expires_on = serializers.DateField()
    status = serializers.ChoiceField(choices=GiftCard.Status.choices)
    sold_on_site = serializers.BooleanField()
    pro_name = serializers.CharField()
    pro_slug = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()


class GiftCardOfferSerializer(serializers.Serializer):
    pro_name = serializers.CharField()
    currency = serializers.CharField()
    min_minor = serializers.IntegerField()
    max_minor = serializers.IntegerField()
    suggestions = serializers.ListField(child=serializers.IntegerField())
    validity_days = serializers.IntegerField()


class BuyGiftCardInputSerializer(serializers.Serializer):
    amount_minor = serializers.IntegerField(min_value=1)
    recipient_name = serializers.CharField(max_length=80)
    recipient_contact = serializers.CharField(max_length=120, required=False, allow_blank=True)
    message = serializers.CharField(max_length=300, required=False, allow_blank=True)
    from_name = serializers.CharField(max_length=80, required=False, allow_blank=True)


class SellGiftCardInputSerializer(serializers.Serializer):
    amount_minor = serializers.IntegerField(min_value=1)
    method = serializers.ChoiceField(choices=OnSitePayment.Method.choices)
    recipient_name = serializers.CharField(max_length=80, required=False, allow_blank=True)


class RedeemInputSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=20)
    amount_minor = serializers.IntegerField(min_value=1)
    appointment_id = serializers.UUIDField(required=False, allow_null=True)


class GiftCardCheckSerializer(serializers.Serializer):
    code = serializers.CharField()
    balance_minor = serializers.IntegerField()
    currency = serializers.CharField()
    expires_on = serializers.DateField()


# --- Stock --------------------------------------------------------------------------------------


def item_payload(item: StockItem) -> dict:
    quantity = item.variant.stock if item.variant_id else item.quantity
    return {
        "id": str(item.pk),
        "name": item.name,
        "ean": item.ean,
        "kind": item.kind,
        "unit": item.unit,
        "quantity": quantity,
        "alert_threshold": item.alert_threshold,
        "low": quantity <= item.alert_threshold,
        "variant_id": str(item.variant_id) if item.variant_id else None,
        "cost_minor": item.cost_minor,
        "is_active": item.is_active,
    }


class StockItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    ean = serializers.CharField(allow_blank=True)
    kind = serializers.ChoiceField(choices=StockItem.Kind.choices)
    unit = serializers.ChoiceField(choices=StockItem.Unit.choices)
    quantity = serializers.IntegerField()
    alert_threshold = serializers.IntegerField()
    low = serializers.BooleanField()
    variant_id = serializers.UUIDField(allow_null=True)
    cost_minor = serializers.IntegerField(allow_null=True)
    is_active = serializers.BooleanField()


class StockItemInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    kind = serializers.ChoiceField(choices=StockItem.Kind.choices)
    unit = serializers.ChoiceField(choices=StockItem.Unit.choices, required=False)
    ean = serializers.CharField(max_length=20, required=False, allow_blank=True)
    alert_threshold = serializers.IntegerField(min_value=0, required=False)
    quantity = serializers.IntegerField(min_value=0, required=False)
    cost_minor = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    variant_id = serializers.UUIDField(required=False, allow_null=True)


class MovementSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=StockMovement.Kind.choices)
    change = serializers.IntegerField()
    after = serializers.IntegerField()
    note = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()


def movement_payload(movement: StockMovement) -> dict:
    return {
        "id": str(movement.pk),
        "kind": movement.kind,
        "change": movement.change,
        "after": movement.after,
        "note": movement.note,
        "created_at": _iso(movement.created_at),
    }


class StockMoveInputSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(
        choices=[(k, v) for k, v in StockMovement.Kind.choices if k not in ("use", "inventory")]
    )
    quantity = serializers.IntegerField(min_value=1)
    note = serializers.CharField(max_length=120, required=False, allow_blank=True)


class CountInputSerializer(serializers.Serializer):
    counted = serializers.IntegerField(min_value=0)


class ConsumptionRowSerializer(serializers.Serializer):
    item_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class ConsumptionInputSerializer(serializers.Serializer):
    rows = ConsumptionRowSerializer(many=True)


# --- Payments at the salon ----------------------------------------------------------------------


def on_site_payload(payment: OnSitePayment) -> dict:
    return {
        "id": str(payment.pk),
        "label": payment.label,
        "amount_minor": payment.amount_minor,
        "currency": payment.currency,
        "method": payment.method,
        "reference": payment.reference,
        "appointment_id": str(payment.appointment_id) if payment.appointment_id else None,
        "client_name": payment.record.name if payment.record_id else "",
        "created_at": _iso(payment.created_at),
        "cancelled": payment.cancelled_at is not None,
    }


class OnSitePaymentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    label = serializers.CharField()
    amount_minor = serializers.IntegerField()
    currency = serializers.CharField()
    method = serializers.ChoiceField(choices=OnSitePayment.Method.choices)
    reference = serializers.CharField(allow_blank=True)
    appointment_id = serializers.UUIDField(allow_null=True)
    client_name = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()
    cancelled = serializers.BooleanField()


class OnSitePaymentInputSerializer(serializers.Serializer):
    amount_minor = serializers.IntegerField(min_value=1)
    method = serializers.ChoiceField(choices=OnSitePayment.Method.choices)
    label = serializers.CharField(max_length=120, required=False, allow_blank=True)
    reference = serializers.CharField(max_length=60, required=False, allow_blank=True)
    appointment_id = serializers.UUIDField(required=False, allow_null=True)
    record_id = serializers.UUIDField(required=False, allow_null=True)


class PaymentMethodsSerializer(serializers.Serializer):
    methods = serializers.ListField(
        child=serializers.ChoiceField(choices=OnSitePayment.Method.choices)
    )
    terminal_configured = serializers.BooleanField()
    certified_till = serializers.BooleanField()
    currency = serializers.CharField()


class ReasonInputSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=120)


# --- Campaigns ----------------------------------------------------------------------------------


def campaign_payload(campaign: Campaign) -> dict:
    return {
        "id": str(campaign.pk),
        "name": campaign.name,
        "segment": campaign.segment,
        "inactive_days": campaign.inactive_days,
        "channel": campaign.channel,
        "subject": campaign.subject,
        "body": campaign.body,
        "status": campaign.status,
        "sent_at": _iso(campaign.sent_at),
        "stats": campaigns.stats(campaign) if campaign.status == Campaign.Status.SENT else None,
    }


class CampaignStatsSerializer(serializers.Serializer):
    targeted = serializers.IntegerField()
    without_consent = serializers.IntegerField()
    pending = serializers.IntegerField()
    sent = serializers.IntegerField()
    failed = serializers.IntegerField()
    unsubscribed = serializers.IntegerField()
    returned = serializers.IntegerField()


class CampaignSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    segment = serializers.ChoiceField(choices=Campaign.Segment.choices)
    inactive_days = serializers.IntegerField()
    channel = serializers.ChoiceField(choices=Channel.choices)
    subject = serializers.CharField(allow_blank=True)
    body = serializers.CharField()
    status = serializers.ChoiceField(choices=Campaign.Status.choices)
    sent_at = serializers.DateTimeField(allow_null=True)
    stats = CampaignStatsSerializer(allow_null=True)


class CampaignInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80)
    segment = serializers.ChoiceField(choices=Campaign.Segment.choices)
    inactive_days = serializers.IntegerField(min_value=7, max_value=730, required=False)
    channel = serializers.ChoiceField(choices=Channel.choices)
    subject = serializers.CharField(max_length=120, required=False, allow_blank=True)
    body = serializers.CharField(max_length=1000)


class AudienceSerializer(serializers.Serializer):
    recipients = serializers.IntegerField()
    without_consent = serializers.IntegerField()
    limit = serializers.IntegerField(allow_null=True)
    sent_this_month = serializers.IntegerField()


class UnsubscribeSerializer(serializers.Serializer):
    pro_name = serializers.CharField()
    channel = serializers.ChoiceField(choices=Channel.choices)
    unsubscribed = serializers.BooleanField()


class ClientPackagesSerializer(serializers.Serializer):
    packages = SoldPackageSerializer(many=True)
    gift_cards = GiftCardSerializer(many=True)


class PublicPackagesSerializer(serializers.Serializer):
    packages = PackageSerializer(many=True)
    gift_cards = GiftCardOfferSerializer(allow_null=True)
