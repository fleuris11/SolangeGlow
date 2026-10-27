from rest_framework import serializers

from apps.core.media.api import MediaSerializer

from .models import LiveHand, LiveRoom

KIND_CHOICES = LiveRoom.Kind.choices
STATUS_CHOICES = [
    ("scheduled", "scheduled"),
    ("on_air", "on_air"),
    ("ended", "ended"),
    ("cancelled", "cancelled"),
]


class LiveHostSerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.CharField(allow_null=True)
    photo = MediaSerializer(allow_null=True)


class LiveQuestionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    text = serializers.CharField()
    at_second = serializers.IntegerField()
    answered = serializers.BooleanField()
    mine = serializers.BooleanField()
    held = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class LiveHandSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    name = serializers.CharField()
    status = serializers.ChoiceField(choices=LiveHand.Status.choices)
    raised_at = serializers.DateTimeField()


class LiveReplaySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[("processing", "processing"), ("ready", "ready")])
    until = serializers.DateTimeField(allow_null=True)
    urls = serializers.DictField(child=serializers.CharField())
    duration = serializers.FloatField(allow_null=True)


class LivePinSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    slug = serializers.CharField()
    name = serializers.CharField()
    price_minor = serializers.IntegerField()
    currency = serializers.CharField()
    photo = MediaSerializer(allow_null=True)
    in_stock = serializers.BooleanField()
    pinned = serializers.BooleanField(help_text="On screen now (else: shown earlier).")


class LiveSaleSerializer(serializers.Serializer):
    shop_slug = serializers.CharField()
    pins = LivePinSerializer(many=True)
    orders_count = serializers.IntegerField()
    revenue_minor = serializers.IntegerField(allow_null=True, help_text="Seen by the host only.")
    currency = serializers.CharField()


class LiveStateSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=KIND_CHOICES)
    source_id = serializers.UUIDField()
    title = serializers.CharField()
    status = serializers.ChoiceField(choices=STATUS_CHOICES)
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    time_zone = serializers.CharField()
    can_start_at = serializers.DateTimeField()
    started_at = serializers.DateTimeField(allow_null=True)
    ends_by = serializers.DateTimeField(allow_null=True)
    host = LiveHostSerializer()
    is_host = serializers.BooleanField()
    can_watch = serializers.BooleanField()
    can_ask = serializers.BooleanField()
    can_raise_hand = serializers.BooleanField()
    signed_in = serializers.BooleanField()
    viewers = serializers.IntegerField()
    max_viewers = serializers.IntegerField()
    speaking = serializers.BooleanField()
    my_hand = serializers.ChoiceField(choices=LiveHand.Status.choices, allow_null=True)
    hands = LiveHandSerializer(many=True)
    questions = LiveQuestionSerializer(many=True)
    replay = LiveReplaySerializer(allow_null=True)
    link = serializers.CharField()
    cover_url = serializers.CharField()
    sale = LiveSaleSerializer(allow_null=True)


class LiveJoinSerializer(serializers.Serializer):
    url = serializers.CharField()
    room = serializers.CharField()
    token = serializers.CharField()
    identity = serializers.CharField()
    host = serializers.BooleanField()
    host_identity = serializers.CharField()
    expires_at = serializers.DateTimeField()


class LiveQuestionInputSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=300)


class UpcomingLiveSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=KIND_CHOICES)
    source_id = serializers.UUIDField()
    title = serializers.CharField()
    starts_at = serializers.DateTimeField()
    time_zone = serializers.CharField(help_text="Time zone of the country of the live.")
    on_air = serializers.BooleanField()
    host = LiveHostSerializer()
    link = serializers.CharField()
    cover_url = serializers.CharField()


class LiveQuotaSerializer(serializers.Serializer):
    used = serializers.IntegerField()
    allowed = serializers.IntegerField()
