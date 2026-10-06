from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttling import SettingRateThrottle

from . import services
from .purposes import PURPOSES


class MediaSerializer(serializers.Serializer):
    """What the web app needs to show a media (see services.asset_payload)."""

    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=["image", "video", "audio"])
    status = serializers.ChoiceField(
        choices=["pending", "processing", "ready", "rejected", "failed"]
    )
    error = serializers.CharField(allow_null=True)
    blurhash = serializers.CharField(allow_null=True)
    width = serializers.IntegerField(allow_null=True)
    height = serializers.IntegerField(allow_null=True)
    duration = serializers.FloatField(allow_null=True)
    urls = serializers.DictField(child=serializers.CharField())


MediaPayload = MediaSerializer


class MediaUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    purpose = serializers.ChoiceField(choices=sorted(PURPOSES))
    kind = serializers.ChoiceField(choices=["image", "video", "audio"], required=False)


class MediaUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "media_upload"

    @extend_schema(tags=["media"], request=MediaUploadSerializer, responses={202: MediaPayload})
    def post(self, request):
        serializer = MediaUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        asset = services.create_asset(
            owner=request.user,
            uploaded=serializer.validated_data["file"],
            purpose=serializer.validated_data["purpose"],
            kind=serializer.validated_data.get("kind"),
        )
        return Response(services.asset_payload(asset), status=status.HTTP_202_ACCEPTED)


class MediaDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["media"], responses=MediaPayload)
    def get(self, request, asset_id):
        return Response(services.asset_payload(services.get_for_owner(asset_id, request.user)))
