"""Glow Pro in the back office: the plans (prices, limits, what they unlock), the
subscriptions (start a trial or end one in a click), the widgets."""

from __future__ import annotations

from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TabbedTranslationAdmin
from unfold.admin import TabularInline
from unfold.decorators import action, display

from apps.core.audit.admin import AuditedModelAdmin
from apps.core.errors import DomainError
from apps.core.money import Money

from . import services
from .models import Plan, PlanPrice, Subscription, SubscriptionPeriod, Widget

STATUS_LABELS = {"trialing": "info", "active": "success", "past_due": "warning", "ended": "danger"}


class PriceInline(TabularInline):
    model = PlanPrice
    fields = ["country", "currency", "amount_minor"]
    extra = 0
    tab = True


@admin.register(Plan)
class PlanAdmin(AuditedModelAdmin, TabbedTranslationAdmin):
    list_display = ["name", "key", "trial_days", "is_default", "is_active", "position"]
    list_editable = ["is_active", "position"]
    fields = [
        "key",
        "name",
        "description",
        "is_default",
        "features",
        "limits",
        "trial_days",
        "position",
        "is_active",
    ]
    inlines = [PriceInline]

    def get_readonly_fields(self, request, obj=None):
        return ["key"] if obj else []


class PeriodInline(TabularInline):
    model = SubscriptionPeriod
    fields = ["plan", "starts_at", "ends_at", "is_trial", "payment"]
    readonly_fields = fields
    extra = 0
    tab = True

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Subscription)
class SubscriptionAdmin(AuditedModelAdmin):
    list_display = ["pro", "plan", "status_badge", "current_period_end", "cancel_at_period_end"]
    list_filter = ["status", "plan", "pro__country"]
    search_fields = ["pro__business_name", "pro__slug"]
    readonly_fields = [
        "pro",
        "plan",
        "status",
        "trial_used",
        "current_period_end",
        "grace_until",
        "cancel_at_period_end",
        "renewal_payment",
        "renewal_noticed_at",
        "next_plan",
    ]
    inlines = [PeriodInline]
    actions_detail = ["end_detail"]

    def has_add_permission(self, request):
        return False

    @display(description=_("status"), ordering="status", label=STATUS_LABELS)
    def status_badge(self, subscription):
        return subscription.status, subscription.get_status_display()

    @action(description=_("Back to the free plan now"), url_path="end", icon="block")
    def end_detail(self, request, object_id):
        subscription = get_object_or_404(Subscription, pk=object_id)
        try:
            services.downgrade(subscription)
        except DomainError as exc:
            self.message_user(request, exc.text(), messages.ERROR)
        else:
            self.message_user(request, _("Done; the pro is told."))
        return redirect(reverse("admin:glowpro_subscription_change", args=[object_id]))


@admin.register(Widget)
class WidgetAdmin(AuditedModelAdmin):
    list_display = ["pro", "color", "domains", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["pro__business_name"]
    readonly_fields = ["pro"]

    def has_add_permission(self, request):
        return False

    @display(description=_("allowed websites"))
    def domains(self, widget):
        return ", ".join(widget.allowed_domains) or "—"


@admin.register(PlanPrice)
class PlanPriceAdmin(AuditedModelAdmin):
    list_display = ["plan", "country", "price"]
    list_filter = ["plan", "country"]

    @display(description=_("price per month"))
    def price(self, row):
        return Money(row.amount_minor, row.currency).format("fr")
