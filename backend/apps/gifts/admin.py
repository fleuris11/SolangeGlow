"""Gifts from abroad in the back office: the list, what each gift paid, the link sent again,
a gift cancelled and refunded in euros (unused), and the FCFA the platform must cover."""

from __future__ import annotations

from django.contrib import admin, messages
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from unfold.admin import TabularInline
from unfold.decorators import display

from apps.core.audit.admin import AuditedModelAdmin
from apps.core.errors import DomainError
from apps.core.money import Money

from . import selectors, services
from .models import Gift, GiftPhoto, GiftUse


def money(value, currency) -> str:
    return Money(value or 0, currency).format("fr")


class UseInline(TabularInline):
    model = GiftUse
    extra = 0
    tab = True
    fields = ["created_at", "label", "source_type", "amount_minor", "refunded_minor", "payment"]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class PhotoInline(TabularInline):
    model = GiftPhoto
    extra = 0
    tab = True
    fields = ["created_at", "source", "media"]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Gift)
class GiftAdmin(AuditedModelAdmin):
    list_display = [
        "reference",
        "kind",
        "recipient_name",
        "giver",
        "show_value",
        "show_balance",
        "status",
        "occasion",
        "send_at",
        "expires_on",
    ]
    list_filter = ["status", "kind", "occasion", "proof_status"]
    search_fields = ["reference", "recipient_name", "from_name", "giver__email", "title"]
    date_hierarchy = "created_at"
    inlines = [UseInline, PhotoInline]
    actions = ["resend_link", "cancel_and_refund"]
    readonly_fields = [
        "reference",
        "kind",
        "status",
        "giver",
        "recipient_user",
        "code",
        "value_minor",
        "balance_minor",
        "currency",
        "price_minor",
        "price_currency",
        "rate",
        "payment",
        "pro",
        "service",
        "variant",
        "selection_product",
        "zone",
        "delivery_minor",
        "sent_at",
        "opened_at",
        "cancel_until",
        "proof_media",
        "proof_status",
        "proof_sent_at",
        "message_media",
    ]
    fields = [
        "reference",
        "kind",
        "status",
        "title",
        "giver",
        "from_name",
        "recipient_name",
        "recipient_phone",
        "recipient_email",
        "recipient_user",
        "language",
        "occasion",
        "message",
        "message_media",
        "send_at",
        "sent_at",
        "opened_at",
        "code",
        "value_minor",
        "balance_minor",
        "currency",
        "price_minor",
        "price_currency",
        "rate",
        "payment",
        "pro",
        "service",
        "variant",
        "selection_product",
        "zone",
        "delivery_minor",
        "expires_on",
        "cancel_until",
        "proof_media",
        "proof_status",
        "proof_sent_at",
    ]

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @display(description=_("value"))
    def show_value(self, obj):
        return money(obj.value_minor, obj.currency)

    @display(description=_("left"))
    def show_balance(self, obj):
        return money(obj.balance_minor, obj.currency)

    def changelist_view(self, request, extra_context=None):
        start = timezone.localtime().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month = selectors.owed(since=start)
        total = selectors.owed()
        messages.info(
            request,
            _(
                "Paid by gifts in FCFA this month: %(month)s (%(count)s uses). "
                "Since the start: %(total)s. To cover with the euros received."
            )
            % {
                "month": money(month["xof_minor"], "XOF"),
                "count": month["count"],
                "total": money(total["xof_minor"], "XOF"),
            },
        )
        return super().changelist_view(request, extra_context)

    @admin.action(description=_("Send the link again to the person"))
    def resend_link(self, request, queryset):
        done = 0
        for gift in queryset:
            try:
                services.resend(gift, actor=request.user)
                done += 1
            except DomainError as exc:
                self.message_user(request, f"{gift}: {exc.text()}", messages.WARNING)
        self.message_user(request, _("%(count)s links sent again.") % {"count": done})

    @admin.action(description=_("Cancel and refund in euros (unused gifts)"))
    def cancel_and_refund(self, request, queryset):
        done = 0
        for gift in queryset:
            try:
                services.cancel(gift, actor=request.user)
                done += 1
            except DomainError as exc:
                self.message_user(request, f"{gift}: {exc.text()}", messages.WARNING)
        self.message_user(request, _("%(count)s gifts cancelled.") % {"count": done})


@admin.register(GiftUse)
class GiftUseAdmin(AuditedModelAdmin):
    list_display = ["created_at", "gift", "label", "source_type", "show_amount", "show_refunded"]
    list_filter = ["source_type"]
    search_fields = ["gift__reference", "label", "payment__reference"]
    readonly_fields = [
        "gift",
        "payment",
        "amount_minor",
        "refunded_minor",
        "label",
        "source_type",
        "source_id",
    ]

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @display(description=_("amount"))
    def show_amount(self, obj):
        return money(obj.amount_minor, obj.gift.currency)

    @display(description=_("given back"))
    def show_refunded(self, obj):
        return money(obj.refunded_minor, obj.gift.currency)
