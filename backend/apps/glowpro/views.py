from __future__ import annotations

import datetime

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttling import SettingRateThrottle
from apps.accounts.views_base import OptionalAuthView
from apps.invoicing.models import Document
from apps.pros.hours import zone_of
from apps.pros.services import get_pro

from . import errors, services, stats
from . import serializers as s
from .models import Widget


class ProView(APIView):
    """Pages of the pro herself (her plan, her dashboard, her widget)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "salon"

    def get_throttles(self):
        return super().get_throttles() if self.request.method != "GET" else []

    def pro(self, request):
        return get_pro(request.user)


def _my_glowpro(pro) -> Response:
    pro.__dict__.pop("_glowpro_subscription", None)
    subscription = services.subscription_for(pro)
    invoices = Document.objects.filter(
        source_type="glowpro", buyer_user=pro.user, issuer__is_platform=True
    ).order_by("-issued_at")[:24]
    return Response(s.my_glowpro_payload(pro, subscription, invoices))


class MyGlowProView(ProView):
    @extend_schema(tags=["glowpro"], responses=s.MyGlowProSerializer)
    def get(self, request):
        return _my_glowpro(self.pro(request))


class TrialView(ProView):
    @extend_schema(
        tags=["glowpro"], request=s.PlanChoiceSerializer, responses=s.MyGlowProSerializer
    )
    def post(self, request):
        data = s.PlanChoiceSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        pro = self.pro(request)
        services.start_trial(pro, data.validated_data["plan"], actor=request.user)
        return _my_glowpro(pro)


class SubscribeView(ProView):
    @extend_schema(
        tags=["glowpro"], request=s.PlanChoiceSerializer, responses=s.CheckoutUrlSerializer
    )
    def post(self, request):
        data = s.PlanChoiceSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        payment = services.subscribe(
            self.pro(request), data.validated_data["plan"], actor=request.user
        )
        return Response({"checkout_url": payment.checkout_url})


class CancelView(ProView):
    @extend_schema(tags=["glowpro"], request=None, responses=s.MyGlowProSerializer)
    def post(self, request):
        pro = self.pro(request)
        services.cancel(pro, actor=request.user)
        return _my_glowpro(pro)


class ResumeView(ProView):
    @extend_schema(tags=["glowpro"], request=None, responses=s.MyGlowProSerializer)
    def post(self, request):
        pro = self.pro(request)
        services.resume(pro, actor=request.user)
        return _my_glowpro(pro)


class DashboardView(ProView):
    @extend_schema(
        tags=["glowpro"], parameters=[s.DashboardQuerySerializer], responses=s.DashboardSerializer
    )
    def get(self, request):
        query = s.DashboardQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        pro = self.pro(request)
        today = timezone.now().astimezone(zone_of(pro)).date()
        start = query.validated_data.get("start") or today.replace(day=1)
        end = query.validated_data.get("end") or today
        if end - start > datetime.timedelta(days=stats.MAX_DAYS):
            end = start + datetime.timedelta(days=stats.MAX_DAYS - 1)
        result = stats.dashboard(pro, start, end, today)
        return Response({**result, "currency": pro.currency or "XOF"})


class MyWidgetView(ProView):
    @extend_schema(tags=["glowpro"], responses=s.WidgetSerializer)
    def get(self, request):
        pro = self.pro(request)
        return Response(s.widget_payload(pro, Widget.objects.filter(pro=pro).first()))

    @extend_schema(tags=["glowpro"], request=s.WidgetInputSerializer, responses=s.WidgetSerializer)
    def put(self, request):
        data = s.WidgetInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        pro = self.pro(request)
        widget = services.save_widget(pro, **data.validated_data)
        return Response(s.widget_payload(pro, widget))


class PublicWidgetView(OptionalAuthView):
    """What the embedded booking needs: colour and the websites allowed to show it."""

    throttle_scope = "widget"

    @extend_schema(tags=["glowpro"], responses=s.PublicWidgetSerializer)
    def get(self, request, slug):
        widget = services.widget_for(slug)
        if widget is None:
            raise errors.NotAllowedHere()
        return Response(
            {
                "slug": widget.pro.slug,
                "name": widget.pro.display_name,
                "color": widget.color,
                "allowed_domains": list(widget.allowed_domains),
            }
        )
