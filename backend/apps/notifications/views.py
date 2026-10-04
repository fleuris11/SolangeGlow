from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttling import SettingRateThrottle
from apps.core.providers import ProviderNotConfigured

from . import services, vapid
from .models import Notification, PushSubscription


class NotificationSerializer(serializers.ModelSerializer):
    read = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ["id", "event_key", "title", "body", "link", "read", "created_at"]

    def get_read(self, notification) -> bool:
        return notification.read_at is not None


UnreadCount = inline_serializer("UnreadCount", {"unread": serializers.IntegerField()})


class NotificationListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user, in_app=True)

    @extend_schema(tags=["notifications"])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class UnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["notifications"], responses=UnreadCount)
    def get(self, request):
        return Response({"unread": services.unread_count(request.user)})


class MarkReadSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        max_length=200,
        help_text="Leave out to mark everything as read.",
    )


class MarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["notifications"], request=MarkReadSerializer, responses=UnreadCount)
    def post(self, request):
        serializer = MarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data.get("ids")
        services.mark_read(request.user, [str(i) for i in ids] if ids is not None else None)
        return Response({"unread": services.unread_count(request.user)})


class PushKeyView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["notifications"],
        responses=inline_serializer(
            "PushKey", {"public_key": serializers.CharField(allow_null=True)}
        ),
    )
    def get(self, request):
        try:
            return Response({"public_key": vapid.public_key()})
        except ProviderNotConfigured:
            return Response({"public_key": None})


class PushKeysSerializer(serializers.Serializer):
    p256dh = serializers.CharField(max_length=200)
    auth = serializers.CharField(max_length=100)


class PushSubscribeSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=600)
    keys = PushKeysSerializer()


class PushUnsubscribeSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=600)


class PushSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "profile"

    @extend_schema(tags=["notifications"], request=PushSubscribeSerializer, responses={201: None})
    def post(self, request):
        serializer = PushSubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        PushSubscription.objects.update_or_create(
            endpoint=data["endpoint"],
            defaults={
                "user": request.user,
                "p256dh": data["keys"]["p256dh"],
                "auth": data["keys"]["auth"],
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255],
            },
        )
        return Response(status=status.HTTP_201_CREATED)


class PushUnsubscribeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["notifications"], request=PushUnsubscribeSerializer, responses={204: None})
    def post(self, request):
        serializer = PushUnsubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PushSubscription.objects.filter(
            user=request.user, endpoint=serializer.validated_data["endpoint"]
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TestNotificationView(APIView):
    """Sends a test notification to oneself (to try phone alerts)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "notification_test"

    @extend_schema(tags=["notifications"], request=None, responses={202: None})
    def post(self, request):
        services.notify(request.user, "system.test")
        return Response(status=status.HTTP_202_ACCEPTED)
