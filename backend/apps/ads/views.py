from django.http import HttpResponseRedirect
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttling import SettingRateThrottle
from apps.accounts.views_base import OptionalAuthView
from apps.payments.models import Payment
from apps.pros.models import ProProfile

from . import errors, selectors
from . import serializers as s
from .services import boosts, common, delivery, tracking

TAGS = ["ads"]
VISITOR_COOKIE = "sg_visitor"


class AdsView(OptionalAuthView):
    """The ads of a place of a screen (already counted as shown), or the filler."""

    throttle_scope = "ads"

    @extend_schema(tags=TAGS, parameters=[s.AdQuerySerializer], responses=s.AdListSerializer)
    def get(self, request):
        query = s.AdQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        values = query.validated_data
        user = request.user if request.user.is_authenticated else None
        audience = common.audience_of(
            user,
            visitor=request.COOKIES.get(VISITOR_COOKIE, "")[:64],
            country=values["country"].upper(),
            city=values["city"],
            language=getattr(request, "LANGUAGE_CODE", "fr") or "fr",
        )
        placement = values["placement"]
        chosen = delivery.pick(
            placement,
            audience,
            count=values["count"],
            context={"city": values["city"], "trade": values["trade"]},
        )
        payload = {
            "results": [selectors.ad_payload(c, placement) for c in chosen],
            "adsense": None
            if chosen or not common.ads_on(audience)
            else selectors.filler_payload(placement),
            "feed_every": max(2, int(common.setting("ads.feed_every", 6))),
            "splash_seconds": int(common.setting("ads.splash_seconds", 5)),
        }
        return Response(s.AdListSerializer(payload).data)


class ClickView(OptionalAuthView):
    """Counts a click, then opens the page of the advertiser."""

    throttle_scope = "ads"

    @extend_schema(tags=TAGS, responses={302: None})
    def get(self, request, token):
        try:
            target = tracking.click(token, request.user)
        except errors.AdNotFound:
            target = "/"
        return HttpResponseRedirect(target)


def _pro(user) -> ProProfile:
    pro = ProProfile.objects.select_related("country").filter(user=user).first()
    if pro is None:
        raise errors.NotAPro()
    return pro


class BoostView(APIView):
    """« Boost my showcase »: prices, the running boost, past boosts and their figures."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "ads"

    @extend_schema(tags=TAGS, responses=s.BoostPageSerializer)
    def get(self, request):
        return Response(s.BoostPageSerializer(selectors.boost_payload(_pro(request.user))).data)

    @extend_schema(tags=TAGS, request=s.BoostBuySerializer, responses=s.BoostCheckoutSerializer)
    def post(self, request):
        data = s.BoostBuySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        boost = boosts.buy(_pro(request.user), data.validated_data["duration"], actor=request.user)
        payment = Payment.objects.get(pk=boost.payment_id)
        return Response(s.BoostCheckoutSerializer({"checkout_url": payment.checkout_url}).data)
