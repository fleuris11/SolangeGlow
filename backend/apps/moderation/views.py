from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.throttling import SettingRateThrottle

from . import errors, services
from .models import Block, Reason

TARGETS = {
    "post": ("social", "post"),
    "comment": ("social", "comment"),
    "story": ("social", "story"),
    "review": ("social", "review"),
    "product": ("shop", "product"),
    "person": ("accounts", "user"),
}


def find_target(kind: str, target_id):
    app_label, model = TARGETS[kind]
    model_class = ContentType.objects.get_by_natural_key(app_label, model).model_class()
    target = model_class.objects.filter(pk=target_id).first()
    if target is None:
        raise errors.UnknownTarget()
    return target


class TargetSerializer(serializers.Serializer):
    target = serializers.ChoiceField(choices=sorted(TARGETS))
    id = serializers.UUIDField()


class ReportSerializer(TargetSerializer):
    reason = serializers.ChoiceField(choices=Reason.choices)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)


class BlockedPersonSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class ReportView(APIView):
    """Report a post, a comment, a story, a review, a product or a person to the team."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "report"

    @extend_schema(tags=["moderation"], request=ReportSerializer, responses={201: None})
    def post(self, request):
        data = ReportSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        services.report(
            request.user,
            find_target(values["target"], values["id"]),
            reason=values["reason"],
            comment=values.get("comment", ""),
        )
        return Response(status=status.HTTP_201_CREATED)


class BlockView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["moderation"], request=None, responses={204: None})
    def post(self, request, user_id):
        services.block(request.user, get_object_or_404(User, pk=user_id))
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(tags=["moderation"], request=None, responses={204: None})
    def delete(self, request, user_id):
        services.unblock(request.user, get_object_or_404(User, pk=user_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyBlocksView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["moderation"], responses=BlockedPersonSerializer(many=True))
    def get(self, request):
        rows = Block.objects.filter(blocker=request.user).select_related("blocked")
        return Response([{"id": b.blocked_id, "name": b.blocked.first_name} for b in rows])


class HideView(APIView):
    """« Hide »: a post, a story, a comment, or every post of a person."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["moderation"], request=TargetSerializer, responses={204: None})
    def post(self, request):
        data = TargetSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        target = find_target(data.validated_data["target"], data.validated_data["id"])
        services.hide(request.user, target)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(tags=["moderation"], request=TargetSerializer, responses={204: None})
    def delete(self, request):
        data = TargetSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        target = find_target(data.validated_data["target"], data.validated_data["id"])
        services.unhide(request.user, target)
        return Response(status=status.HTTP_204_NO_CONTENT)
