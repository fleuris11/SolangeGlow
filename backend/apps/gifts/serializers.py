from rest_framework import serializers

from apps.core.media.api import MediaSerializer

from .models import Gift, Occasion

KIND_CHOICES = Gift.Kind.choices
STATUS_CHOICES = Gift.Status.choices
PROOF_CHOICES = [("", "none"), ("sent", "sent"), ("declined", "declined")]


class GiftAmountSerializer(serializers.Serializer):
    amount_minor = serializers.IntegerField()
    currency = serializers.CharField()


class GiftProSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    photo = MediaSerializer(allow_null=True)
    city = serializers.CharField()


class GiftThingSerializer(serializers.Serializer):
    name = serializers.CharField()
    photo = MediaSerializer(allow_null=True)
    available = serializers.BooleanField()
    duration_minutes = serializers.IntegerField(required=False)
    variant = serializers.CharField(required=False)
    delivery_mode = serializers.CharField(required=False)
    zone = serializers.CharField(required=False)


class GiftUseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    label = serializers.CharField()
    kind = serializers.CharField()
    amount = GiftAmountSerializer()
    refunded = GiftAmountSerializer()
    payment_status = serializers.CharField()
    created_at = serializers.DateTimeField()
    starts_at = serializers.DateTimeField(allow_null=True)
    status = serializers.CharField()
    link = serializers.CharField(required=False)
    receipt_code = serializers.CharField(allow_null=True, required=False)
    pickup_point = serializers.CharField()


class GiftPickupPointSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    city = serializers.CharField()
    address = serializers.CharField()
    hours = serializers.CharField()


class GiftPhotoSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    source = serializers.CharField()
    media = MediaSerializer()


class GiftReceptionSerializer(serializers.Serializer):
    """The page of the gift (only the first fields while it is not open yet)."""

    status = serializers.ChoiceField(choices=STATUS_CHOICES)
    kind = serializers.ChoiceField(choices=KIND_CHOICES)
    locked = serializers.BooleanField()
    opens_at = serializers.DateTimeField()
    is_giver = serializers.BooleanField()
    from_name = serializers.CharField()
    recipient_name = serializers.CharField()
    occasion = serializers.ChoiceField(choices=Occasion.choices)
    message = serializers.CharField(required=False)
    message_media = MediaSerializer(allow_null=True, required=False)
    title = serializers.CharField(required=False)
    value = GiftAmountSerializer(required=False)
    balance = GiftAmountSerializer(required=False)
    expires_on = serializers.DateField(required=False)
    expired = serializers.BooleanField(required=False)
    cancelled = serializers.BooleanField(required=False)
    usable = serializers.BooleanField(required=False)
    unused = serializers.BooleanField(required=False)
    code = serializers.CharField(allow_null=True, required=False)
    claimed = serializers.BooleanField(required=False)
    pro = GiftProSerializer(allow_null=True, required=False)
    service_id = serializers.UUIDField(allow_null=True, required=False)
    thing = GiftThingSerializer(required=False)
    uses = GiftUseSerializer(many=True, required=False)
    pickup_points = GiftPickupPointSerializer(many=True, required=False)
    recipient_phone = serializers.CharField(required=False)
    time_zone = serializers.CharField(required=False)
    photos = GiftPhotoSerializer(many=True, required=False)
    proof_status = serializers.ChoiceField(choices=PROOF_CHOICES, required=False)
    proof_sent_id = serializers.UUIDField(allow_null=True, required=False)


class GiftStepSerializer(serializers.Serializer):
    key = serializers.ChoiceField(choices=["paid", "sent", "opened", "used", "photo"])
    at = serializers.DateTimeField(allow_null=True)


class GiftSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    reference = serializers.CharField()
    kind = serializers.ChoiceField(choices=KIND_CHOICES)
    status = serializers.ChoiceField(choices=STATUS_CHOICES)
    title = serializers.CharField()
    recipient_name = serializers.CharField()
    occasion = serializers.ChoiceField(choices=Occasion.choices)
    send_at = serializers.DateTimeField()
    value = GiftAmountSerializer()
    balance = GiftAmountSerializer()
    paid = GiftAmountSerializer(allow_null=True)
    created_at = serializers.DateTimeField()
    proof_status = serializers.ChoiceField(choices=PROOF_CHOICES)
    pro = GiftProSerializer(allow_null=True)
    photo = MediaSerializer(allow_null=True)


class GiftSentSerializer(GiftSummarySerializer):
    from_name = serializers.CharField()
    recipient_phone = serializers.CharField()
    message = serializers.CharField()
    message_media = MediaSerializer(allow_null=True)
    link = serializers.CharField()
    code = serializers.CharField(allow_null=True)
    price = GiftAmountSerializer()
    fee = GiftAmountSerializer(allow_null=True)
    payment_id = serializers.UUIDField(allow_null=True)
    payment_status = serializers.CharField()
    checkout_url = serializers.CharField()
    expires_on = serializers.DateField()
    cancel_until = serializers.DateTimeField(allow_null=True)
    can_cancel = serializers.BooleanField()
    can_resend = serializers.BooleanField()
    steps = GiftStepSerializer(many=True)
    uses = GiftUseSerializer(many=True)
    proof = MediaSerializer(allow_null=True)


class GiftReceivedSerializer(GiftSummarySerializer):
    from_name = serializers.CharField()
    token = serializers.CharField()
    code = serializers.CharField(allow_null=True)
    expires_on = serializers.DateField()


class GiftQuoteQuerySerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=KIND_CHOICES)
    service = serializers.UUIDField(required=False)
    variant = serializers.UUIDField(required=False)
    delivery_mode = serializers.CharField(required=False, allow_blank=True, default="")
    zone = serializers.UUIDField(required=False)
    selection_product = serializers.UUIDField(required=False)
    option = serializers.CharField(required=False, allow_blank=True, default="")
    amount_minor = serializers.IntegerField(required=False, help_text="Euro cents (card).")


class GiftZoneSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    mode = serializers.CharField()
    name = serializers.CharField()
    fee = GiftAmountSerializer()


class GiftQuoteSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=KIND_CHOICES)
    title = serializers.CharField()
    value = GiftAmountSerializer()
    price = GiftAmountSerializer()
    fee = GiftAmountSerializer()
    total = GiftAmountSerializer()
    rate = serializers.CharField()
    card_min = GiftAmountSerializer()
    card_max = GiftAmountSerializer()
    validity_days = serializers.IntegerField()
    cancel_days = serializers.IntegerField()
    message_max_seconds = serializers.IntegerField()
    photo = MediaSerializer(allow_null=True)
    pro = GiftProSerializer(allow_null=True)


class GiftOptionsSerializer(serializers.Serializer):
    """What a product gift may choose: its hand-over modes and zones."""

    pickup = serializers.BooleanField()
    zones = GiftZoneSerializer(many=True)


class GiftIdeaSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=KIND_CHOICES)
    id = serializers.UUIDField()
    slug = serializers.CharField()
    shop = serializers.CharField()
    shop_name = serializers.CharField()
    title = serializers.CharField()
    photo = MediaSerializer(allow_null=True)
    price = GiftAmountSerializer()


class GiftIdeasSerializer(serializers.Serializer):
    products = GiftIdeaSerializer(many=True)
    selection = GiftIdeaSerializer(many=True)
    card_min = GiftAmountSerializer()
    card_max = GiftAmountSerializer()


class GiftCreateSerializer(GiftQuoteQuerySerializer):
    recipient_name = serializers.CharField(max_length=80)
    recipient_phone = serializers.CharField(max_length=30)
    recipient_email = serializers.EmailField(required=False, allow_blank=True, default="")
    language = serializers.ChoiceField(choices=["fr", "en", "sk"], default="fr")
    occasion = serializers.ChoiceField(choices=Occasion.choices, default=Occasion.NONE)
    message = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    message_media_id = serializers.UUIDField(required=False, allow_null=True)
    send_at = serializers.DateTimeField(required=False, allow_null=True)
    from_name = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")


class GiftCheckoutSerializer(serializers.Serializer):
    gift = GiftSentSerializer()
    checkout_url = serializers.CharField()


class GiftBookSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    staff_id = serializers.UUIDField(required=False, allow_null=True)
    guest_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    guest_phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class GiftReceiveSerializer(serializers.Serializer):
    address = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    landmarks = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    pickup_point_id = serializers.UUIDField(required=False, allow_null=True)


class GiftPaySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=20)
    payment_id = serializers.UUIDField(required=False, allow_null=True)
    group_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        if bool(attrs.get("payment_id")) == bool(attrs.get("group_id")):
            raise serializers.ValidationError("payment_id or group_id")
        return attrs


class GiftPaidSerializer(serializers.Serializer):
    balance = GiftAmountSerializer()


class GlowCardCheckSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=20)


class GlowCardSerializer(serializers.Serializer):
    balance = GiftAmountSerializer()
    expires_on = serializers.DateField()
    from_name = serializers.CharField()


class GiftProofSerializer(serializers.Serializer):
    media_id = serializers.UUIDField(required=False, allow_null=True)
    send = serializers.BooleanField()


class GiftPhotoUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
