"""Salon management in the back office, mostly read only: what belongs to the pros is
managed by them. The team sees packages, gift cards, stock, payments at the salon,
campaigns and consents (for questions and data requests)."""

from __future__ import annotations

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import TabularInline
from unfold.decorators import display

from apps.core.audit.admin import AuditedModelAdmin
from apps.core.money import Money

from .models import (
    Campaign,
    ClientPackage,
    GiftCard,
    GiftCardUse,
    MarketingConsent,
    OnSitePayment,
    Package,
    StockItem,
    StockMovement,
)
from .services import campaigns


def money(value, currency) -> str:
    return Money(value or 0, currency).format("fr")


class ReadOnlyAdmin(AuditedModelAdmin):
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ReadOnlyInline(TabularInline):
    extra = 0
    tab = True

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Package)
class PackageAdmin(ReadOnlyAdmin):
    list_display = ["name", "pro", "sessions", "price", "max_installments", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "pro__business_name"]

    @display(description=_("price"))
    def price(self, package):
        return money(package.price_minor, package.currency)


@admin.register(ClientPackage)
class ClientPackageAdmin(ReadOnlyAdmin):
    list_display = [
        "package",
        "pro",
        "record",
        "sessions_used",
        "sessions_total",
        "status",
        "expires_on",
    ]
    list_filter = ["status"]
    search_fields = ["package__name", "pro__business_name", "record__name"]


class UseInline(ReadOnlyInline):
    model = GiftCardUse
    fields = ["created_at", "amount_minor", "online", "appointment"]
    readonly_fields = fields


@admin.register(GiftCard)
class GiftCardAdmin(ReadOnlyAdmin):
    list_display = ["code", "pro", "amount", "balance", "status", "expires_on", "sold_on_site"]
    list_filter = ["status", "sold_on_site"]
    search_fields = ["code", "pro__business_name", "recipient_name"]
    exclude = ["recipient_contact"]  # personal
    inlines = [UseInline]

    @display(description=_("amount"))
    def amount(self, card):
        return money(card.amount_minor, card.currency)

    @display(description=_("balance"))
    def balance(self, card):
        return money(card.balance_minor, card.currency)


class MovementInline(ReadOnlyInline):
    model = StockMovement
    fields = ["created_at", "kind", "change", "after", "note"]
    readonly_fields = fields


@admin.register(StockItem)
class StockItemAdmin(ReadOnlyAdmin):
    list_display = ["name", "pro", "kind", "quantity", "alert_threshold", "ean", "is_active"]
    list_filter = ["kind", "is_active"]
    search_fields = ["name", "ean", "pro__business_name"]
    inlines = [MovementInline]


@admin.register(OnSitePayment)
class OnSitePaymentAdmin(ReadOnlyAdmin):
    """Money the pros took themselves: not in the ledger, not a certified till."""

    list_display = ["created_at", "pro", "label", "amount", "method", "cancelled_at"]
    list_filter = ["method", "pro__country"]
    search_fields = ["pro__business_name", "label", "reference"]
    date_hierarchy = "created_at"

    @display(description=_("amount"))
    def amount(self, payment):
        return money(payment.amount_minor, payment.currency)


@admin.register(Campaign)
class CampaignAdmin(ReadOnlyAdmin):
    list_display = ["name", "pro", "segment", "channel", "status", "sent_at", "summary"]
    list_filter = ["status", "channel", "segment"]
    search_fields = ["name", "pro__business_name"]

    @display(description=_("sent / not sent"))
    def summary(self, campaign):
        if campaign.status != Campaign.Status.SENT:
            return "—"
        stats = campaigns.stats(campaign)
        return f"{stats['sent']} / {stats['failed']}"


@admin.register(MarketingConsent)
class MarketingConsentAdmin(ReadOnlyAdmin):
    list_display = ["record", "channel", "granted", "source", "changed_at"]
    list_filter = ["channel", "granted", "source"]
    search_fields = ["record__name", "record__pro__business_name"]
