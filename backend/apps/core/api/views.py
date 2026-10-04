from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import Country


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
