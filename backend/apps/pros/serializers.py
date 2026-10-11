from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.core.media.api import MediaSerializer
from apps.core.media.services import asset_payload

from . import hours, selectors
from .models import (
    Closure,
    OpeningPeriod,
    PortfolioItem,
    ProProfile,
    ProVerification,
    Service,
    ServiceCategory,
    ServiceOption,
    ServiceStep,
    SocialNetwork,
    SpokenLanguage,
    Trade,
)
from .services import missing_for_publication, short_link


class TradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trade
        fields = ["key", "name", "icon"]


def _media(asset):
    return asset_payload(asset)


Media = MediaSerializer(allow_null=True)


# --- Services ----------------------------------------------------------------------------


class StepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceStep
        fields = ["kind", "label", "duration_minutes"]
        extra_kwargs = {"label": {"required": False}}


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceOption
        fields = ["name", "price_minor", "extra_minutes"]
        extra_kwargs = {"price_minor": {"required": False}, "extra_minutes": {"required": False}}


class ServicePhotoSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    media = MediaSerializer()


class ServiceSerializer(serializers.ModelSerializer):
    category_id = serializers.UUIDField(allow_null=True)
    trade = serializers.SlugRelatedField(slug_field="key", read_only=True, allow_null=True)
    steps = StepSerializer(many=True)
    options = OptionSerializer(many=True)
    photos = serializers.SerializerMethodField()
    work_minutes = serializers.IntegerField()
    waiting_minutes = serializers.IntegerField()

    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "description",
            "category_id",
            "trade",
            "price_kind",
            "price_minor",
            "currency",
            "duration_minutes",
            "work_minutes",
            "waiting_minutes",
            "available_at_home",
            "is_active",
            "position",
            "steps",
            "options",
            "photos",
        ]
        extra_kwargs = {field: {"required": True} for field in fields}

    @extend_schema_field(ServicePhotoSerializer(many=True))
    def get_photos(self, service):
        return [
            {"id": photo.pk, "media": _media(photo.media)}
            for photo in service.photos.all()
            if photo.media.is_ready or self.context.get("owner")
        ]


class ServiceWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80)
    description = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    trade_key = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    price_kind = serializers.ChoiceField(choices=Service.PriceKind.choices)
    price_minor = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    available_at_home = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)
    position = serializers.IntegerField(required=False, min_value=0)
    steps = StepSerializer(many=True, required=False)
    options = OptionSerializer(many=True, required=False)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ["id", "name", "position"]
        read_only_fields = ["id"]
        extra_kwargs = {"position": {"required": False}}


# --- Hours -------------------------------------------------------------------------------


class PeriodSerializer(serializers.ModelSerializer):
    opens_at = serializers.TimeField(format="%H:%M")
    closes_at = serializers.TimeField(format="%H:%M")

    class Meta:
        model = OpeningPeriod
        fields = ["weekday", "opens_at", "closes_at"]


class ClosureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Closure
        fields = ["id", "starts_on", "ends_on", "reason"]
        read_only_fields = ["id"]
        extra_kwargs = {"reason": {"required": False}}


class HoursSerializer(serializers.Serializer):
    periods = PeriodSerializer(many=True)
    closures = ClosureSerializer(many=True, read_only=True)


class OpeningStatusSerializer(serializers.Serializer):
    is_open = serializers.BooleanField()
    closes_at = serializers.DateTimeField(allow_null=True)
    next_opening = serializers.DateTimeField(allow_null=True)
    closed_today = serializers.BooleanField()
    has_hours = serializers.BooleanField()
    time_zone = serializers.CharField()


def opening_payload(pro: ProProfile) -> dict:
    status = hours.opening_status(pro)
    return {
        "is_open": status.is_open,
        "closes_at": status.closes_at,
        "next_opening": status.next_opening,
        "closed_today": status.closed_today,
        "has_hours": status.has_hours,
        "time_zone": str(hours.zone_of(pro)),
    }


# --- Portfolio ---------------------------------------------------------------------------


class PortfolioItemSerializer(serializers.ModelSerializer):
    media = serializers.SerializerMethodField()
    before = serializers.SerializerMethodField()
    service_id = serializers.UUIDField(allow_null=True)
    service_name = serializers.SerializerMethodField()

    class Meta:
        model = PortfolioItem
        fields = ["id", "media", "before", "caption", "service_id", "service_name", "position"]
        extra_kwargs = {field: {"required": True} for field in fields}

    @extend_schema_field(MediaSerializer())
    def get_media(self, item):
        return _media(item.media)

    @extend_schema_field(Media)
    def get_before(self, item):
        return _media(item.before_media)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_service_name(self, item):
        return item.service.name if item.service_id else None


class PortfolioUploadSerializer(serializers.Serializer):
    file = serializers.FileField(help_text="Picture or video of the result.")
    before = serializers.FileField(required=False, help_text="Optional picture before.")
    caption = serializers.CharField(required=False, allow_blank=True, max_length=200)
    service_id = serializers.UUIDField(required=False, allow_null=True)


class PortfolioUpdateSerializer(serializers.Serializer):
    caption = serializers.CharField(required=False, allow_blank=True, max_length=200)
    service_id = serializers.UUIDField(required=False, allow_null=True)
    position = serializers.IntegerField(required=False, min_value=0)


# --- Showcase ----------------------------------------------------------------------------


class LanguageSerializer(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()


class PlaceSerializer(serializers.Serializer):
    country = serializers.CharField(allow_null=True)
    city = serializers.CharField()
    district = serializers.CharField()
    receives_clients = serializers.BooleanField()
    address = serializers.CharField(allow_null=True)
    latitude = serializers.FloatField(allow_null=True)
    longitude = serializers.FloatField(allow_null=True)
    directions_url = serializers.CharField(allow_null=True)
    landmarks = serializers.CharField()
    landmarks_voice = MediaSerializer(allow_null=True)
    itinerary_video = MediaSerializer(allow_null=True)


class TravelSerializer(serializers.Serializer):
    travels_to_clients = serializers.BooleanField()
    radius_km = serializers.IntegerField(allow_null=True)
    area = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField()), allow_null=True
    )
    fee_minor = serializers.IntegerField(allow_null=True)
    currency = serializers.CharField()


def directions_url(pro: ProProfile) -> str | None:
    if pro.location is None:
        return None
    return (
        "https://www.google.com/maps/dir/?api=1&destination="
        f"{pro.location.y:.6f},{pro.location.x:.6f}"
    )


def place_payload(pro: ProProfile, *, private: bool) -> dict:
    """The exact place is shown only when the pro receives clients (or to herself)."""
    visible = private or pro.receives_clients
    ready = (lambda a: a) if private else (lambda a: a if a is not None and a.is_ready else None)
    return {
        "country": pro.country.code if pro.country_id else None,
        "city": pro.city,
        "district": pro.district,
        "receives_clients": pro.receives_clients,
        "address": (pro.address or None) if visible else None,
        "latitude": pro.location.y if visible and pro.location else None,
        "longitude": pro.location.x if visible and pro.location else None,
        "directions_url": directions_url(pro) if visible else None,
        "landmarks": pro.landmarks if visible else "",
        "landmarks_voice": _media(ready(pro.landmarks_voice)) if visible else None,
        "itinerary_video": _media(ready(pro.itinerary_video)) if visible else None,
    }


def travel_payload(pro: ProProfile) -> dict:
    return {
        "travels_to_clients": pro.travels_to_clients,
        "radius_km": pro.service_radius_km if pro.travels_to_clients else None,
        "area": list(pro.service_area.coords[0]) if pro.service_area else None,
        "fee_minor": pro.travel_fee_minor if pro.travels_to_clients else None,
        "currency": pro.currency,
    }


class ShowcaseSerializer(serializers.Serializer):
    """Public page of a pro (also its preview for herself)."""

    slug = serializers.CharField()
    short_link = serializers.CharField()
    business_name = serializers.CharField()
    kind = serializers.ChoiceField(choices=ProProfile.Kind.choices)
    status = serializers.ChoiceField(choices=ProProfile.Status.choices)
    bio = serializers.CharField()
    bio_voice = MediaSerializer(allow_null=True)
    photo = MediaSerializer(allow_null=True)
    cover = MediaSerializer(allow_null=True)
    trades = TradeSerializer(many=True)
    social_links = serializers.DictField(child=serializers.CharField())
    languages = LanguageSerializer(many=True)
    verified = serializers.BooleanField()
    rating_average = serializers.FloatField(allow_null=True)
    rating_count = serializers.IntegerField()
    currency = serializers.CharField()
    opening = OpeningStatusSerializer()
    hours = PeriodSerializer(many=True)
    closures = ClosureSerializer(many=True)
    categories = CategorySerializer(many=True)
    services = ServiceSerializer(many=True)
    portfolio = PortfolioItemSerializer(many=True)
    place = PlaceSerializer()
    travel = TravelSerializer()
    published_at = serializers.DateTimeField(allow_null=True)
    updated_at = serializers.DateTimeField()


def showcase_payload(pro: ProProfile, *, private: bool = False) -> dict:
    ready = (lambda a: a) if private else (lambda a: a if a is not None and a.is_ready else None)
    labels = dict(SpokenLanguage.choices)
    today = timezone.localdate()
    services = getattr(pro, "visible_services", None)
    if services is None:
        services = list(selectors.visible_services().filter(pro=pro))
    portfolio = [item for item in pro.portfolio.all() if private or item.media.is_ready]
    return {
        "slug": pro.slug or "",
        "short_link": short_link(pro) if pro.slug else "",
        "business_name": pro.display_name,
        "kind": pro.kind,
        "status": pro.status,
        "bio": pro.bio,
        "bio_voice": _media(ready(pro.bio_voice)),
        "photo": _media(ready(pro.photo)),
        "cover": _media(ready(pro.cover)),
        "trades": TradeSerializer(pro.trades.all(), many=True).data,
        "social_links": {k: v for k, v in pro.social_links.items() if k in SocialNetwork.values},
        "languages": [{"code": c, "label": str(labels.get(c, c))} for c in pro.languages],
        "verified": pro.is_verified,
        "rating_average": float(pro.rating_average) if pro.rating_average is not None else None,
        "rating_count": pro.rating_count,
        "currency": pro.currency,
        "opening": opening_payload(pro),
        "hours": PeriodSerializer(pro.opening_periods.all(), many=True).data,
        "closures": ClosureSerializer(selectors.upcoming_closures(pro, today), many=True).data,
        "categories": CategorySerializer(pro.categories.all(), many=True).data,
        "services": ServiceSerializer(services, many=True, context={"owner": private}).data,
        "portfolio": PortfolioItemSerializer(portfolio, many=True).data,
        "place": place_payload(pro, private=private),
        "travel": travel_payload(pro),
        "published_at": pro.published_at,
        "updated_at": pro.updated_at,
    }


class VerificationStateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ProProfile.Verification.choices)
    rejection_reason = serializers.CharField(allow_null=True)
    submitted_at = serializers.DateTimeField(allow_null=True)
    can_collect_payments = serializers.BooleanField()


def verification_payload(pro: ProProfile) -> dict:
    last = pro.verifications.order_by("-created_at").first()
    return {
        "status": pro.verification_status,
        "rejection_reason": (last.rejection_reason or None)
        if last and last.status == ProVerification.Status.REJECTED
        else None,
        "submitted_at": last.created_at if last else None,
        "can_collect_payments": selectors.can_collect_payments(pro),
    }


class MyProSerializer(ShowcaseSerializer):
    """The pro's own showcase, with what only she sees."""

    missing = serializers.ListField(child=serializers.CharField())
    verification = VerificationStateSerializer()
    suspension_reason = serializers.CharField(allow_null=True)


def my_pro_payload(pro: ProProfile) -> dict:
    return {
        **showcase_payload(pro, private=True),
        "missing": missing_for_publication(pro),
        "verification": verification_payload(pro),
        "suspension_reason": pro.suspension_reason or None
        if pro.status == ProProfile.Status.SUSPENDED
        else None,
    }


class BecomeProSerializer(serializers.Serializer):
    business_name = serializers.CharField(max_length=80)
    kind = serializers.ChoiceField(choices=ProProfile.Kind.choices, required=False)
    trades = serializers.ListField(child=serializers.CharField(), required=False)
    city = serializers.CharField(max_length=80, required=False, allow_blank=True)
    district = serializers.CharField(max_length=80, required=False, allow_blank=True)


class ProUpdateSerializer(serializers.Serializer):
    business_name = serializers.CharField(max_length=80, required=False)
    slug = serializers.CharField(max_length=40, required=False)
    kind = serializers.ChoiceField(choices=ProProfile.Kind.choices, required=False)
    bio = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    trades = serializers.ListField(child=serializers.CharField(), required=False)
    social_links = serializers.DictField(
        child=serializers.CharField(allow_blank=True), required=False
    )
    languages = serializers.ListField(
        child=serializers.ChoiceField(choices=SpokenLanguage.choices), required=False
    )
    city = serializers.CharField(max_length=80, required=False, allow_blank=True)
    district = serializers.CharField(max_length=80, required=False, allow_blank=True)
    address = serializers.CharField(max_length=200, required=False, allow_blank=True)
    landmarks = serializers.CharField(max_length=500, required=False, allow_blank=True)
    receives_clients = serializers.BooleanField(required=False)


class LocationSerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    source = serializers.ChoiceField(
        choices=ProProfile.LocationSource.choices, required=False, default="map"
    )


class TravelUpdateSerializer(serializers.Serializer):
    travels_to_clients = serializers.BooleanField()
    radius_km = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    area = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField(), min_length=2, max_length=2),
        required=False,
        allow_null=True,
    )
    fee_minor = serializers.IntegerField(required=False, allow_null=True, min_value=0)


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()


class SlugCheckSerializer(serializers.Serializer):
    slug = serializers.CharField()
    available = serializers.BooleanField()
    short_link = serializers.CharField()


class VerificationUploadSerializer(serializers.Serializer):
    document_type = serializers.ChoiceField(choices=ProVerification.DocumentType.choices)
    document = serializers.ImageField()
    selfie = serializers.ImageField()


# --- Search ------------------------------------------------------------------------------


class SearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True, max_length=120)
    trade = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    district = serializers.CharField(required=False, allow_blank=True)
    lat = serializers.FloatField(required=False, min_value=-90, max_value=90)
    lng = serializers.FloatField(required=False, min_value=-180, max_value=180)
    radius_km = serializers.FloatField(required=False, min_value=0.5)
    price_max = serializers.IntegerField(required=False, min_value=0)
    currency = serializers.CharField(required=False, allow_blank=True, max_length=3)
    rating_min = serializers.FloatField(required=False, min_value=0, max_value=5)
    open_now = serializers.BooleanField(required=False)
    at_home = serializers.BooleanField(required=False)
    verified = serializers.BooleanField(required=False)
    sort = serializers.ChoiceField(
        choices=["relevance", "distance", "rating", "price"], required=False
    )
    cursor = serializers.CharField(required=False, allow_blank=True)


class MapQuerySerializer(SearchQuerySerializer):
    bbox = serializers.CharField(help_text="min_lng,min_lat,max_lng,max_lat")

    def validate_bbox(self, value):
        try:
            west, south, east, north = (float(x) for x in value.split(","))
        except ValueError as exc:
            raise serializers.ValidationError("min_lng,min_lat,max_lng,max_lat") from exc
        if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
            raise serializers.ValidationError("min_lng,min_lat,max_lng,max_lat")
        return (west, south, east, north)


class CardSerializer(serializers.Serializer):
    slug = serializers.CharField()
    business_name = serializers.CharField()
    photo = MediaSerializer(allow_null=True)
    trades = TradeSerializer(many=True)
    city = serializers.CharField()
    district = serializers.CharField()
    distance_m = serializers.IntegerField(allow_null=True)
    latitude = serializers.FloatField(allow_null=True)
    longitude = serializers.FloatField(allow_null=True)
    rating_average = serializers.FloatField(allow_null=True)
    rating_count = serializers.IntegerField()
    min_price = serializers.IntegerField(allow_null=True)
    currency = serializers.CharField()
    open_now = serializers.BooleanField()
    receives_clients = serializers.BooleanField()
    travels_to_clients = serializers.BooleanField()
    verified = serializers.BooleanField()


def card_payload(pro: ProProfile) -> dict:
    distance = getattr(pro, "distance", None)
    meters = None
    if distance is not None:
        meters = int(distance.m)
        if not pro.receives_clients:  # never reveal a private address by its distance
            meters = max(1000, round(meters / 1000) * 1000)
    public = pro.receives_clients and pro.location is not None
    photo = pro.photo if pro.photo is not None and pro.photo.is_ready else None
    return {
        "slug": pro.slug,
        "business_name": pro.display_name,
        "photo": _media(photo),
        "trades": TradeSerializer(pro.trades.all(), many=True).data,
        "city": pro.city,
        "district": pro.district,
        "distance_m": meters,
        "latitude": pro.location.y if public else None,
        "longitude": pro.location.x if public else None,
        "rating_average": float(pro.rating_average) if pro.rating_average is not None else None,
        "rating_count": pro.rating_count,
        "min_price": getattr(pro, "min_price", None),
        "currency": pro.currency,
        "open_now": hours.opening_status(pro).is_open,
        "receives_clients": pro.receives_clients,
        "travels_to_clients": pro.travels_to_clients,
        "verified": pro.is_verified,
    }


class SearchResultsSerializer(serializers.Serializer):
    results = CardSerializer(many=True)
    next = serializers.CharField(allow_null=True)
    count = serializers.IntegerField()


class MapFeaturePropertiesSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    trade = serializers.CharField(allow_null=True)
    rating = serializers.FloatField(allow_null=True)
    verified = serializers.BooleanField()


class MapFeatureSerializer(serializers.Serializer):
    type = serializers.CharField()
    geometry = serializers.DictField()
    properties = MapFeaturePropertiesSerializer()


class MapResultsSerializer(serializers.Serializer):
    type = serializers.CharField()
    features = MapFeatureSerializer(many=True)
    truncated = serializers.BooleanField()


class CitySerializer(serializers.Serializer):
    country = serializers.CharField()
    city = serializers.CharField()
    pros = serializers.IntegerField()
    districts = serializers.ListField(child=serializers.CharField())


class MapConfigSerializer(serializers.Serializer):
    style_url = serializers.CharField()
    attribution = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    zoom = serializers.FloatField()


class ArrivalSerializer(serializers.Serializer):
    sent = serializers.BooleanField()
