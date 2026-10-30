from rest_framework import serializers

from apps.core.media.api import MediaSerializer

from .models import Boost, Creative, Placement


class AdTradeSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()


class AdProSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    photo = MediaSerializer(allow_null=True)
    city = serializers.CharField(allow_blank=True)
    trades = AdTradeSerializer(many=True)
    rating_average = serializers.FloatField(allow_null=True)
    rating_count = serializers.IntegerField()
    verified = serializers.BooleanField()


class AdProductSerializer(serializers.Serializer):
    title = serializers.CharField()
    price_minor = serializers.IntegerField()
    currency = serializers.CharField()
    photo = MediaSerializer(allow_null=True)
    seller = serializers.CharField()


class AdSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    placement = serializers.ChoiceField(choices=Placement.choices)
    format = serializers.ChoiceField(choices=Creative.Format.choices)
    sponsor = serializers.CharField()
    house = serializers.BooleanField()
    title = serializers.CharField(allow_blank=True)
    text = serializers.CharField(allow_blank=True)
    cta = serializers.CharField(allow_blank=True)
    click_url = serializers.CharField()
    media = MediaSerializer(many=True)
    pro = AdProSerializer(allow_null=True)
    product = AdProductSerializer(allow_null=True)


class AdSenseSerializer(serializers.Serializer):
    client = serializers.CharField()
    slot = serializers.CharField()


class AdListSerializer(serializers.Serializer):
    results = AdSerializer(many=True)
    adsense = AdSenseSerializer(allow_null=True)
    # One sponsored post every N posts of the feed; seconds of the launch screen.
    feed_every = serializers.IntegerField()
    splash_seconds = serializers.IntegerField()


class AdQuerySerializer(serializers.Serializer):
    placement = serializers.ChoiceField(choices=Placement.choices)
    count = serializers.IntegerField(required=False, default=1, min_value=1, max_value=10)
    city = serializers.CharField(required=False, default="", allow_blank=True, max_length=80)
    country = serializers.CharField(required=False, default="", allow_blank=True, max_length=2)
    trade = serializers.CharField(required=False, default="", allow_blank=True, max_length=40)


class BoostPricesSerializer(serializers.Serializer):
    currency = serializers.CharField()
    day = serializers.IntegerField()
    week = serializers.IntegerField()


class BoostRowSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    duration = serializers.ChoiceField(choices=Boost.Duration.choices)
    status = serializers.ChoiceField(choices=Boost.Status.choices)
    amount_minor = serializers.IntegerField()
    currency = serializers.CharField()
    starts_at = serializers.DateTimeField(allow_null=True)
    ends_at = serializers.DateTimeField(allow_null=True)
    impressions = serializers.IntegerField()
    clicks = serializers.IntegerField()


class BoostPageSerializer(serializers.Serializer):
    open = serializers.BooleanField()
    prices = BoostPricesSerializer(allow_null=True)
    running_until = serializers.DateTimeField(allow_null=True)
    boosts = BoostRowSerializer(many=True)


class BoostBuySerializer(serializers.Serializer):
    duration = serializers.ChoiceField(choices=Boost.Duration.choices)


class BoostCheckoutSerializer(serializers.Serializer):
    checkout_url = serializers.CharField()
