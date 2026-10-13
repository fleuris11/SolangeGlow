from rest_framework import serializers

from apps.core.media.api import MediaSerializer
from apps.core.media.services import asset_payload
from apps.core.selectors import get_setting
from apps.messaging.payloads import person_payload
from apps.messaging.serializers import PersonSerializer

from .models import Dispute, Payment, Payout, PayoutMethod
from .services import receipt_code_for
from .services.common import S


def _iso(value):
    return value.isoformat() if value else None


def dispute_payload(dispute: Dispute | None) -> dict | None:
    if dispute is None:
        return None
    return {
        "id": str(dispute.pk),
        "reason": dispute.reason,
        "status": dispute.status,
        "description": dispute.description,
        "response_due_at": _iso(dispute.response_due_at),
        "decision": dispute.decision or None,
        "refund_minor": dispute.refund_minor,
        "note": dispute.note,
        "conversation_id": str(dispute.conversation_id) if dispute.conversation_id else None,
        "evidence": [
            {
                "id": str(item.pk),
                "author_id": str(item.author_id) if item.author_id else None,
                "text": item.text,
                "media": asset_payload(item.media),
                "created_at": _iso(item.created_at),
            }
            for item in dispute.evidence.select_related("media")
        ],
    }


def payment_payload(payment: Payment, viewer) -> dict:
    """What each side sees: the client her code, the seller her commission and net."""
    is_seller = payment.seller_id == viewer.pk
    is_buyer = payment.buyer_id == viewer.pk
    status = payment.status
    try:
        dispute = payment.dispute
    except Dispute.DoesNotExist:
        dispute = None
    max_attempts = int(
        get_setting("escrow.receipt_code_max_attempts", country=payment.country or None, default=5)
    )
    return {
        "id": str(payment.pk),
        "reference": payment.reference,
        "description": payment.description,
        "purpose": payment.purpose,
        "status": status,
        "role": "seller" if is_seller else "buyer",
        "currency": payment.currency,
        "items_minor": payment.items_minor,
        "delivery_minor": payment.delivery_minor,
        "buyer_fee_minor": payment.buyer_fee_minor,
        "total_minor": payment.total_minor,
        "commission_minor": payment.commission_minor if is_seller else None,
        "seller_net_minor": payment.seller_gross_minor - payment.commission_minor
        if is_seller
        else None,
        "refunded_minor": payment.refunded_minor,
        "delivery_mode": payment.delivery_mode,
        "carrier": payment.carrier,
        "tracking_number": payment.tracking_number,
        "expected_delivery_at": _iso(payment.expected_delivery_at),
        "delivered_at": _iso(payment.delivered_at),
        "delivery_proof": asset_payload(payment.delivery_proof),
        "service_at": _iso(payment.service_at),
        "created_at": _iso(payment.created_at),
        "expires_at": _iso(payment.expires_at),
        "paid_at": _iso(payment.paid_at),
        "shipped_at": _iso(payment.shipped_at),
        "released_at": _iso(payment.released_at),
        "refunded_at": _iso(payment.refunded_at),
        "cancelled_at": _iso(payment.cancelled_at),
        "end_reason": payment.end_reason,
        "provider": payment.provider,
        "checkout_url": payment.checkout_url if is_buyer and status == S.PENDING_PAYMENT else "",
        "buyer": person_payload(payment.buyer),
        "seller": person_payload(payment.seller),
        "receipt_code": receipt_code_for(payment, viewer) if is_buyer else None,
        "code_attempts_left": max(max_attempts - payment.receipt_code_attempts, 0)
        if is_seller
        else None,
        "dispute": dispute_payload(dispute),
        "can": {
            "pay": is_buyer and status == S.PENDING_PAYMENT,
            "ship": is_seller
            and status == S.HELD
            and payment.delivery_mode != Payment.Delivery.SERVICE,
            "deliver": is_seller and status == S.SHIPPED and payment.delivered_at is None,
            "confirm": is_seller and status in (S.HELD, S.SHIPPED),
            "cancel": status == S.HELD,
            "dispute": is_buyer and status in (S.HELD, S.SHIPPED),
            "new_code": is_buyer and status in (S.HELD, S.SHIPPED),
        },
    }


class EvidenceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    author_id = serializers.UUIDField(allow_null=True)
    text = serializers.CharField(allow_blank=True)
    media = MediaSerializer(allow_null=True)
    created_at = serializers.DateTimeField()


class DisputeSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    reason = serializers.ChoiceField(choices=Dispute.Reason.choices)
    status = serializers.ChoiceField(choices=Dispute.Status.choices)
    description = serializers.CharField(allow_blank=True)
    response_due_at = serializers.DateTimeField()
    decision = serializers.ChoiceField(choices=Dispute.Decision.choices, allow_null=True)
    refund_minor = serializers.IntegerField()
    note = serializers.CharField(allow_blank=True)
    conversation_id = serializers.UUIDField(allow_null=True)
    evidence = EvidenceSerializer(many=True)


class AbilitiesSerializer(serializers.Serializer):
    pay = serializers.BooleanField()
    ship = serializers.BooleanField()
    deliver = serializers.BooleanField()
    confirm = serializers.BooleanField()
    cancel = serializers.BooleanField()
    dispute = serializers.BooleanField()
    new_code = serializers.BooleanField()


class PaymentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    reference = serializers.CharField()
    description = serializers.CharField()
    purpose = serializers.CharField()
    status = serializers.ChoiceField(choices=Payment.Status.choices)
    role = serializers.ChoiceField(choices=["buyer", "seller"])
    currency = serializers.CharField()
    items_minor = serializers.IntegerField()
    delivery_minor = serializers.IntegerField()
    buyer_fee_minor = serializers.IntegerField()
    total_minor = serializers.IntegerField()
    commission_minor = serializers.IntegerField(allow_null=True)
    seller_net_minor = serializers.IntegerField(allow_null=True)
    refunded_minor = serializers.IntegerField()
    delivery_mode = serializers.ChoiceField(choices=Payment.Delivery.choices)
    carrier = serializers.CharField(allow_blank=True)
    tracking_number = serializers.CharField(allow_blank=True)
    expected_delivery_at = serializers.DateTimeField(allow_null=True)
    delivered_at = serializers.DateTimeField(allow_null=True)
    delivery_proof = MediaSerializer(allow_null=True)
    service_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField(allow_null=True)
    paid_at = serializers.DateTimeField(allow_null=True)
    shipped_at = serializers.DateTimeField(allow_null=True)
    released_at = serializers.DateTimeField(allow_null=True)
    refunded_at = serializers.DateTimeField(allow_null=True)
    cancelled_at = serializers.DateTimeField(allow_null=True)
    end_reason = serializers.CharField(allow_blank=True)
    provider = serializers.CharField()
    checkout_url = serializers.CharField(allow_blank=True)
    buyer = PersonSerializer()
    seller = PersonSerializer()
    receipt_code = serializers.CharField(allow_null=True)
    code_attempts_left = serializers.IntegerField(allow_null=True)
    dispute = DisputeSerializer(allow_null=True)
    can = AbilitiesSerializer()


class PaymentListSerializer(serializers.Serializer):
    results = PaymentSerializer(many=True)


class ShipSerializer(serializers.Serializer):
    carrier = serializers.CharField(required=False, allow_blank=True, max_length=80)
    tracking_number = serializers.CharField(required=False, allow_blank=True, max_length=80)
    expected_delivery_at = serializers.DateTimeField(required=False, allow_null=True)


class DeliveredSerializer(serializers.Serializer):
    proof_media_id = serializers.UUIDField()


class CodeSerializer(serializers.Serializer):
    code = serializers.RegexField(r"^\s*\d{6}\s*$")


class CourierLinkSerializer(serializers.Serializer):
    url = serializers.CharField()


class CourierPaymentSerializer(serializers.Serializer):
    reference = serializers.CharField()
    description = serializers.CharField()
    seller = serializers.CharField()


class OpenDisputeSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(
        choices=[c for c in Dispute.Reason.choices if c[0] != Dispute.Reason.NO_PROOF]
    )
    description = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    media_ids = serializers.ListField(child=serializers.UUIDField(), required=False, max_length=6)


class EvidenceCreateSerializer(serializers.Serializer):
    text = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    media_id = serializers.UUIDField(required=False, allow_null=True)


class TestOutcomeSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=["succeeded", "failed", "abandoned"])


class WalletSerializer(serializers.Serializer):
    currency = serializers.CharField()
    pending_minor = serializers.IntegerField()
    available_minor = serializers.IntegerField()
    in_progress_minor = serializers.IntegerField()
    paid_out_minor = serializers.IntegerField()
    minimum_minor = serializers.IntegerField()
    payout_method = serializers.CharField(allow_null=True)


class WalletLineSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    kind = serializers.CharField()
    account = serializers.ChoiceField(choices=["pending", "available"])
    amount_minor = serializers.IntegerField(help_text="Positive: in; negative: out.")
    reference = serializers.CharField(allow_null=True)
    payment_id = serializers.UUIDField(allow_null=True)


class PayoutSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    amount_minor = serializers.IntegerField()
    currency = serializers.CharField()
    status = serializers.ChoiceField(choices=Payout.Status.choices)
    destination = serializers.CharField()
    created_at = serializers.DateTimeField()
    paid_at = serializers.DateTimeField(allow_null=True)


class WalletOverviewSerializer(serializers.Serializer):
    wallets = WalletSerializer(many=True)
    payouts = PayoutSerializer(many=True)


class PayoutRequestSerializer(serializers.Serializer):
    amount_minor = serializers.IntegerField(min_value=1)
    currency = serializers.CharField(max_length=3)


class PayoutMethodSerializer(serializers.Serializer):
    currency = serializers.CharField(max_length=3)
    kind = serializers.ChoiceField(choices=PayoutMethod.Kind.choices)
    operator = serializers.CharField(required=False, allow_blank=True, max_length=30)
    number = serializers.CharField(required=False, allow_blank=True, max_length=20)
    firstname = serializers.CharField(required=False, allow_blank=True, max_length=80)
    lastname = serializers.CharField(required=False, allow_blank=True, max_length=80)
    account = serializers.CharField(required=False, allow_blank=True, max_length=60)


class PayoutMethodShownSerializer(serializers.Serializer):
    currency = serializers.CharField()
    kind = serializers.ChoiceField(choices=PayoutMethod.Kind.choices)
    display = serializers.CharField()


class TaxProfileSerializer(serializers.Serializer):
    legal_name = serializers.CharField(max_length=150)
    is_business = serializers.BooleanField(required=False)
    business_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    birth_date = serializers.DateField(required=False, allow_null=True)
    address = serializers.CharField(max_length=255)
    postal_code = serializers.CharField(required=False, allow_blank=True, max_length=20)
    city = serializers.CharField(max_length=80)
    country = serializers.CharField(max_length=2)
    tax_id = serializers.CharField(required=False, allow_blank=True, max_length=40, write_only=True)
    tax_id_hint = serializers.CharField(read_only=True)
    vat_number = serializers.CharField(required=False, allow_blank=True, max_length=30)


class DemoPaymentSerializer(serializers.Serializer):
    seller_slug = serializers.SlugField()
    items_minor = serializers.IntegerField(min_value=1)
    delivery_minor = serializers.IntegerField(min_value=0, required=False)
    description = serializers.CharField(max_length=200)
    delivery_mode = serializers.ChoiceField(choices=Payment.Delivery.choices, required=False)
