from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttling import SettingRateThrottle
from apps.accounts.views_base import OptionalAuthView
from apps.core.models import Country

from . import selectors, services
from .serializers import (
    LiveJoinSerializer,
    LiveQuestionInputSerializer,
    LiveQuotaSerializer,
    LiveStateSerializer,
    UpcomingLiveSerializer,
)

TAGS = ["live"]


class LiveView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "live"


class PublicLiveView(OptionalAuthView):
    throttle_scope = "live"


def _state(request, kind, source_id):
    return Response(LiveStateSerializer(services.state(request.user, kind, source_id)).data)


class LiveStateView(PublicLiveView):
    @extend_schema(tags=TAGS, operation_id="live_state", responses=LiveStateSerializer)
    def get(self, request, kind, source_id):
        return _state(request, kind, source_id)


class LiveJoinView(PublicLiveView):
    @extend_schema(tags=TAGS, request=None, responses=LiveJoinSerializer)
    def post(self, request, kind, source_id):
        return Response(LiveJoinSerializer(services.join(request.user, kind, source_id)).data)


class LiveStartView(LiveView):
    @extend_schema(tags=TAGS, request=None, responses=LiveStateSerializer)
    def post(self, request, kind, source_id):
        services.start(request.user, kind, source_id)
        return _state(request, kind, source_id)


class LiveEndView(LiveView):
    @extend_schema(tags=TAGS, request=None, responses=LiveStateSerializer)
    def post(self, request, kind, source_id):
        services.end_by_host(request.user, kind, source_id)
        return _state(request, kind, source_id)


class LiveQuestionsView(LiveView):
    throttle_scope = "live_write"

    @extend_schema(tags=TAGS, request=LiveQuestionInputSerializer, responses=LiveStateSerializer)
    def post(self, request, kind, source_id):
        data = LiveQuestionInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.ask(request.user, kind, source_id, data.validated_data["text"])
        return _state(request, kind, source_id)


class LiveAnsweredView(LiveView):
    @extend_schema(tags=TAGS, request=None, responses=LiveStateSerializer)
    def post(self, request, kind, source_id, question_id):
        services.mark_answered(request.user, kind, source_id, question_id)
        return _state(request, kind, source_id)


class LiveHandView(LiveView):
    throttle_scope = "live_write"

    @extend_schema(
        tags=TAGS, operation_id="live_raise_hand", request=None, responses=LiveStateSerializer
    )
    def post(self, request, kind, source_id):
        services.raise_hand(request.user, kind, source_id)
        return _state(request, kind, source_id)

    @extend_schema(tags=TAGS, operation_id="live_lower_hand", responses={200: LiveStateSerializer})
    def delete(self, request, kind, source_id):
        services.lower_hand(request.user, kind, source_id)
        return _state(request, kind, source_id)


class LiveFloorView(LiveView):
    @extend_schema(
        tags=TAGS, operation_id="live_give_floor", request=None, responses=LiveStateSerializer
    )
    def post(self, request, kind, source_id, user_id):
        services.give_floor(request.user, kind, source_id, user_id)
        return _state(request, kind, source_id)

    @extend_schema(tags=TAGS, operation_id="live_take_floor", responses={200: LiveStateSerializer})
    def delete(self, request, kind, source_id, user_id):
        services.take_floor(request.user, kind, source_id, user_id)
        return _state(request, kind, source_id)


class UpcomingLivesView(PublicLiveView):
    """Lives on air and coming soon (home page), in her country or the one asked."""

    @extend_schema(
        tags=TAGS,
        parameters=[OpenApiParameter("country", str, required=False)],
        responses=UpcomingLiveSerializer(many=True),
    )
    def get(self, request):
        code = request.query_params.get("country") or ""
        country = Country.objects.filter(code=code.upper()).first() if code else None
        if country is None:
            country = selectors.country_of(request.user)
        return Response(UpcomingLiveSerializer(services.upcoming(country), many=True).data)


class LiveQuotaView(LiveView):
    """Her lives of the month (training and sales together) and how many she may plan."""

    @extend_schema(tags=TAGS, responses=LiveQuotaSerializer)
    def get(self, request):
        return Response(LiveQuotaSerializer(selectors.quota(request.user, timezone.now())).data)
