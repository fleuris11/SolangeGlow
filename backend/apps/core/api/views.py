import logging

from django.core.cache import cache
from django.db import connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttling import SettingRateThrottle
from apps.core.geo import search_cities
from apps.core.models import Country
from apps.core.providers import livekit
from apps.core.providers.base import ProviderNotConfigured

logger = logging.getLogger("solangeglow.health")


class HealthView(APIView):
    """Liveness probe used by Docker, the web app and monitoring."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    @extend_schema(
        operation_id="health",
        tags=["system"],
        responses=inline_serializer("Health", {"status": serializers.CharField()}),
    )
    def get(self, request):
        # ?deep=1 (container health check): the database and Redis answer too.
        if request.query_params.get("deep"):
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                cache.get("health")
            except Exception:
                logger.exception("Health check failed")
                return Response({"status": "down"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"status": "ok"})


class CountrySerializer(serializers.ModelSerializer):
    default_currency = serializers.SlugRelatedField(slug_field="code", read_only=True)

    class Meta:
        model = Country
        fields = ["code", "name", "phone_prefix", "default_currency"]


class CountryListView(APIView):
    """Countries open on the platform (phone prefixes, default currency)."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(tags=["catalogue"], responses=CountrySerializer(many=True))
    def get(self, request):
        countries = Country.objects.filter(is_active=True).select_related("default_currency")
        return Response(CountrySerializer(countries, many=True).data)


class CitySearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(max_length=80)
    country = serializers.CharField(required=False, allow_blank=True, max_length=2)


class CitySuggestionSerializer(serializers.Serializer):
    name = serializers.CharField()
    region = serializers.CharField(allow_blank=True)
    postal_code = serializers.CharField(allow_blank=True)
    country = serializers.CharField(source="country.code")
    country_name = serializers.CharField(source="country.name")
    latitude = serializers.FloatField(source="location.y", default=None)
    longitude = serializers.FloatField(source="location.x", default=None)


class CitySearchView(APIView):
    """The cities that start with what is typed, in one country or in the whole world."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "search"

    @extend_schema(
        tags=["catalogue"],
        parameters=[CitySearchQuerySerializer],
        responses=CitySuggestionSerializer(many=True),
    )
    def get(self, request):
        query = CitySearchQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        rows = search_cities(
            query.validated_data["q"], country=query.validated_data.get("country", "")
        )
        return Response(CitySuggestionSerializer(rows, many=True).data)


class LiveKitWebhookView(APIView):
    """Events of the LiveKit server (signed): somebody came in or left, a room closed, a
    recording is ready. Each module handles the rooms of its prefix."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    @extend_schema(exclude=True)
    def post(self, request):
        try:
            event = livekit.client().verify(request.body, request.headers.get("Authorization", ""))
        except (ProviderNotConfigured, ValueError):
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        livekit.dispatch(event)
        return Response({"status": "ok"})
