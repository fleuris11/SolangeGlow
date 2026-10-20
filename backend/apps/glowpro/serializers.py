"""What the web app gets from Glow Pro: plans, subscription, dashboard, widget."""

from __future__ import annotations

from django.conf import settings
from rest_framework import serializers

from apps.booking.models import StaffMember

from . import selectors
from .models import Feature, Subscription


def _iso(value):
    return value.isoformat() if value else None


def plan_payload(plan, country) -> dict:
    price = selectors.price_of(plan, country)
    return {
        "key": plan.key,
        "name": plan.name,
        "description": plan.description,
        "features": list(plan.features or []),
        "limits": {k: int(v) for k, v in (plan.limits or {}).items()},
        "trial_days": plan.trial_days,
        "price_minor": price.amount_minor if price else None,
        "currency": price.currency if price else "",
        "is_default": plan.is_default,
    }


class PlanLimitsSerializer(serializers.Serializer):
    staff = serializers.IntegerField(required=False)
    campaigns_per_month = serializers.IntegerField(required=False)


class GlowPlanSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    features = serializers.ListField(child=serializers.ChoiceField(choices=Feature.choices))
    limits = PlanLimitsSerializer()
    trial_days = serializers.IntegerField()
    price_minor = serializers.IntegerField(allow_null=True)
    currency = serializers.CharField(allow_blank=True)
    is_default = serializers.BooleanField()


class SubscriptionStateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Subscription.Status.choices)
    plan = serializers.CharField()
    trial_used = serializers.BooleanField()
    current_period_end = serializers.DateTimeField(allow_null=True)
    grace_until = serializers.DateTimeField(allow_null=True)
    cancel_at_period_end = serializers.BooleanField()
    payment_due = serializers.BooleanField()


class PlatformInvoiceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    number = serializers.CharField()
    issued_at = serializers.DateTimeField()
    total_minor = serializers.IntegerField()
    currency = serializers.CharField()
    pdf_url = serializers.CharField()


class UsageSerializer(serializers.Serializer):
    staff = serializers.IntegerField()
    staff_limit = serializers.IntegerField(allow_null=True)


class MyGlowProSerializer(serializers.Serializer):
    current = GlowPlanSerializer()
    subscription = SubscriptionStateSerializer()
    plans = GlowPlanSerializer(many=True)
    usage = UsageSerializer()
    invoices = PlatformInvoiceSerializer(many=True)
    is_paying = serializers.BooleanField()


def document_url(document) -> str:
    return f"/api/v1/documents/{document.pk}.pdf"


def my_glowpro_payload(pro, subscription, invoices) -> dict:
    current = selectors.plan_of(pro)
    return {
        "current": plan_payload(current, pro.country),
        "subscription": {
            "status": subscription.status,
            "plan": subscription.plan.key,
            "trial_used": subscription.trial_used,
            "current_period_end": _iso(subscription.current_period_end),
            "grace_until": _iso(subscription.grace_until),
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "payment_due": bool(
                subscription.renewal_payment_id
                and subscription.renewal_payment.status == "pending_payment"
            ),
        },
        "plans": [plan_payload(p, pro.country) for p in selectors.offered_plans()],
        "usage": {
            "staff": StaffMember.objects.filter(pro=pro, is_owner=False, is_active=True).count(),
            "staff_limit": selectors.limit(pro, "staff"),
        },
        "invoices": [
            {
                "id": str(d.pk),
                "number": d.number,
                "issued_at": _iso(d.issued_at),
                "total_minor": d.total_minor,
                "currency": d.currency,
                "pdf_url": document_url(d),
            }
            for d in invoices
        ],
        "is_paying": selectors.is_paying(subscription),
    }


class PlanChoiceSerializer(serializers.Serializer):
    plan = serializers.SlugField(default="premium")


class CheckoutUrlSerializer(serializers.Serializer):
    checkout_url = serializers.CharField()


# --- Dashboard ----------------------------------------------------------------------------------


class DashboardQuerySerializer(serializers.Serializer):
    start = serializers.DateField(required=False)
    end = serializers.DateField(required=False)

    def validate(self, attrs):
        if attrs.get("start") and attrs.get("end") and attrs["end"] < attrs["start"]:
            raise serializers.ValidationError({"end": "before start"})
        return attrs


class BasicStatsSerializer(serializers.Serializer):
    start = serializers.DateField()
    end = serializers.DateField()
    turnover_minor = serializers.IntegerField()
    appointments = serializers.IntegerField()


class StaffStatsSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    color = serializers.CharField()
    appointments = serializers.IntegerField()
    turnover_minor = serializers.IntegerField()
    open_minutes = serializers.IntegerField()
    booked_minutes = serializers.IntegerField()
    occupancy = serializers.IntegerField()


class ServiceStatsSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    appointments = serializers.IntegerField()
    turnover_minor = serializers.IntegerField()


class SeriesPointSerializer(serializers.Serializer):
    day = serializers.DateField()
    turnover_minor = serializers.IntegerField()
    appointments = serializers.IntegerField()


class PeriodStatsSerializer(serializers.Serializer):
    start = serializers.DateField()
    end = serializers.DateField()
    turnover_minor = serializers.IntegerField()
    collected_minor = serializers.IntegerField()
    collected_online_minor = serializers.IntegerField()
    collected_on_site_minor = serializers.IntegerField()
    appointments = serializers.IntegerField()
    average_minor = serializers.IntegerField()
    occupancy = serializers.IntegerField()
    clients = serializers.IntegerField()
    new_clients = serializers.IntegerField()
    loyal_clients = serializers.IntegerField()
    staff = StaffStatsSerializer(many=True)
    services = ServiceStatsSerializer(many=True)
    series = SeriesPointSerializer(many=True)


class DashboardSerializer(serializers.Serializer):
    level = serializers.ChoiceField(choices=[("basic", "basic"), ("complete", "complete")])
    currency = serializers.CharField()
    basic = BasicStatsSerializer()
    current = PeriodStatsSerializer(allow_null=True)
    previous = PeriodStatsSerializer(allow_null=True)


# --- Widget -------------------------------------------------------------------------------------


def snippet(pro) -> str:
    site = settings.SITE_URL.rstrip("/")
    return (
        f'<div data-solangeglow="{pro.slug}"></div>\n<script src="{site}/widget.js" async></script>'
    )


def widget_payload(pro, widget) -> dict:
    return {
        "color": widget.color if widget else "#C8102E",
        "allowed_domains": list(widget.allowed_domains) if widget else [],
        "is_active": bool(widget and widget.is_active),
        "snippet": snippet(pro),
    }


class WidgetSerializer(serializers.Serializer):
    color = serializers.CharField()
    allowed_domains = serializers.ListField(child=serializers.CharField())
    is_active = serializers.BooleanField()
    snippet = serializers.CharField()


class WidgetInputSerializer(serializers.Serializer):
    color = serializers.CharField(max_length=7)
    allowed_domains = serializers.ListField(
        child=serializers.CharField(max_length=255), max_length=10
    )
    is_active = serializers.BooleanField(required=False, default=True)


class PublicWidgetSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    color = serializers.CharField()
    allowed_domains = serializers.ListField(child=serializers.CharField())
