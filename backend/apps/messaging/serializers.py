from rest_framework import serializers

from apps.core.media.api import MediaSerializer
from apps.moderation.models import Reason

from .models import Conversation, ConversationMember, Message


class PersonSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    photo = MediaSerializer(allow_null=True)
    is_pro = serializers.BooleanField()
    pro_slug = serializers.CharField(allow_null=True)
    verified = serializers.BooleanField()
    online = serializers.BooleanField(required=False)
    last_seen = serializers.DateTimeField(allow_null=True, required=False)


class ShareCardSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=Message.ShareKind.choices)
    id = serializers.UUIDField()
    title = serializers.CharField()
    text = serializers.CharField(required=False)
    picture = MediaSerializer(allow_null=True, required=False)
    link = serializers.CharField()
    price_kind = serializers.CharField(required=False)
    amount_minor = serializers.IntegerField(allow_null=True, required=False)
    currency = serializers.CharField(required=False)
    duration_minutes = serializers.IntegerField(allow_null=True, required=False)
    starts_at = serializers.DateTimeField(required=False)


class MessageSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    conversation_id = serializers.UUIDField()
    sender_id = serializers.UUIDField(allow_null=True)
    kind = serializers.ChoiceField(choices=Message.Kind.choices)
    text = serializers.CharField(allow_blank=True)
    media = MediaSerializer(allow_null=True)
    share = ShareCardSerializer(allow_null=True)
    client_id = serializers.UUIDField(allow_null=True)
    fraud_labels = serializers.ListField(child=serializers.CharField())
    is_automatic = serializers.BooleanField()
    state = serializers.ChoiceField(choices=["visible", "held", "removed", "deleted"])
    created_at = serializers.DateTimeField()


class MessagePageSerializer(serializers.Serializer):
    results = MessageSerializer(many=True)
    next = serializers.CharField(allow_null=True, help_text="Older messages: pass as `before`.")


class ReceiptsSerializer(serializers.Serializer):
    delivered_up_to = serializers.DateTimeField(allow_null=True)
    read_up_to = serializers.DateTimeField(allow_null=True)


class ConversationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=Conversation.Kind.choices)
    purpose = serializers.ChoiceField(choices=Conversation.Purpose.choices)
    title = serializers.CharField()
    people = PersonSerializer(many=True)
    status = serializers.ChoiceField(choices=ConversationMember.Status.choices)
    unread = serializers.IntegerField()
    muted = serializers.BooleanField()
    is_closed = serializers.BooleanField()
    payment_warning = serializers.BooleanField()
    last_message = MessageSerializer(allow_null=True)
    last_message_at = serializers.DateTimeField(allow_null=True)
    receipts = ReceiptsSerializer()
    waiting_for_answer = serializers.BooleanField()


class ConversationPageSerializer(serializers.Serializer):
    results = ConversationSerializer(many=True)
    next = serializers.CharField(allow_null=True)


class StartSerializer(serializers.Serializer):
    person_id = serializers.UUIDField()


class ConversationUpdateSerializer(serializers.Serializer):
    muted = serializers.BooleanField(required=False)
    archived = serializers.BooleanField(required=False)


class ShareInputSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=Message.ShareKind.choices)
    id = serializers.UUIDField(required=False)
    pro = serializers.SlugField(required=False, help_text="Free slot: the pro's short name.")
    starts_at = serializers.DateTimeField(required=False, help_text="Free slot: when.")


class MessageCreateSerializer(serializers.Serializer):
    text = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)
    media_id = serializers.UUIDField(required=False, allow_null=True)
    share = ShareInputSerializer(required=False, allow_null=True)
    client_id = serializers.UUIDField(
        required=False, allow_null=True, help_text="Chosen by the device: resending is safe."
    )


class MessageReportSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(choices=Reason.choices)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)


class UnreadSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    requests = serializers.IntegerField()


class QuickRepliesSerializer(serializers.Serializer):
    texts = serializers.ListField(
        child=serializers.CharField(max_length=500, allow_blank=True), max_length=100
    )


class AwayMessageSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    text = serializers.CharField(max_length=500, allow_blank=True)
