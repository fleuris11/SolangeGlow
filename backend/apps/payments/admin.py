"""Finance console: money per currency, payments, disputes decided in one click, refunds to
do by hand, payouts, the ledger (read only), reconciliations and CSV exports (DAC7 too).

Everything here is read only except the pricing rules, the disputes decisions and the
refunds done by hand; each action goes through the services and the audit journal.
"""

from __future__ import annotations

import csv

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _
from unfold.admin import TabularInline
from unfold.decorators import action, display

from apps.core.audit.admin import AuditedModelAdmin
from apps.core.audit.services import record
from apps.core.errors import DomainError
from apps.core.money import Money

from . import ledger, selectors, services
from .models import (
    Dispute,
    DisputeEvidence,
    JournalEntry,
    JournalLine,
    LedgerAccount,
    Payment,
    Payout,
    PricingRule,
    ReconciliationItem,
    ReconciliationRun,
    Refund,
    SellerTaxProfile,
    WebhookEvent,
)
from .services import tax

STATUS_COLORS = {
    "pending_payment": "info",
    "held": "warning",
    "shipped": "warning",
    "disputed": "danger",
    "released": "success",
    "refunded": "info",
    "partially_refunded": "info",
    "cancelled": "info",
}


def amount(value: int | None, currency: str) -> str:
    return "—" if value is None else Money(value, currency).format("fr")


class ReadOnlyAdmin(AuditedModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# --- Ledger --------------------------------------------------------------------------------------


class JournalLineInline(TabularInline):
    model = JournalLine
    fields = ["account", "debit_minor", "credit_minor"]
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(JournalEntry)
class JournalEntryAdmin(ReadOnlyAdmin):
    list_display = ["created_at", "kind", "currency", "payment", "description"]
    list_filter = ["kind", "currency"]
    search_fields = ["payment__reference", "idempotency_key"]
    readonly_fields = [
        "kind",
        "idempotency_key",
        "currency",
        "payment",
        "refund",
        "payout",
        "actor",
        "description",
        "created_at",
    ]
    inlines = [JournalLineInline]


@admin.register(LedgerAccount)
class LedgerAccountAdmin(ReadOnlyAdmin):
    list_display = ["kind", "currency", "owner", "provider", "balance"]
    list_filter = ["kind", "currency", "provider"]
    search_fields = ["owner__first_name", "owner__phone", "owner__email"]

    @display(description=_("balance"))
    def balance(self, account):
        return amount(ledger.balance(account), account.currency)


# --- Payments ------------------------------------------------------------------------------------


class RefundInline(TabularInline):
    model = Refund
    fields = ["amount_minor", "status", "reason", "error", "completed_at"]
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


def _csv(filename: str, header: list[str], rows) -> HttpResponse:
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("﻿")  # Excel opens the accents right
    writer = csv.writer(response, delimiter=";")
    writer.writerow(header)
    writer.writerows(rows)
    return response


@admin.register(Payment)
class PaymentAdmin(ReadOnlyAdmin):
    list_display = [
        "reference",
        "created_at",
        "buyer",
        "seller",
        "total",
        "status_badge",
        "provider",
    ]
    list_filter = ["status", "provider", "currency", "purpose", "country", "delivery_mode"]
    search_fields = ["reference", "provider_reference", "buyer__phone", "seller__phone"]
    date_hierarchy = "created_at"
    inlines = [RefundInline]
    readonly_fields = [
        "reference",
        "status",
        "purpose",
        "description",
        "buyer",
        "seller",
        "breakdown",
        "provider",
        "provider_reference",
        "delivery_mode",
        "carrier",
        "tracking_number",
        "expected_delivery_at",
        "delivered_at",
        "timeline",
        "end_reason",
        "receipt_code_attempts",
        "receipt_code_renewals",
        "entries_list",
    ]
    fields = readonly_fields

    @display(description=_("total paid"))
    def total(self, payment):
        return amount(payment.total_minor, payment.currency)

    @display(description=_("status"), label=STATUS_COLORS)
    def status_badge(self, payment):
        return payment.status, payment.get_status_display()

    @display(description=_("amounts"))
    def breakdown(self, payment):
        c = payment.currency
        rows = [
            (_("Items"), amount(payment.items_minor, c)),
            (_("Delivery"), amount(payment.delivery_minor, c)),
            (_("Buyer protection"), amount(payment.buyer_fee_minor, c)),
            (_("Total paid"), amount(payment.total_minor, c)),
            (_("Commission"), amount(payment.commission_minor, c)),
            (_("Refunded"), amount(payment.refunded_minor, c)),
        ]
        return format_html_join("", "<div>{}: <strong>{}</strong></div>", rows)

    @display(description=_("dates"))
    def timeline(self, payment):
        fields = [
            (_("Created"), payment.created_at),
            (_("Paid"), payment.paid_at),
            (_("Shipped"), payment.shipped_at),
            (_("Disputed"), payment.disputed_at),
            (_("Paid to the seller"), payment.released_at),
            (_("Refunded"), payment.refunded_at),
            (_("Cancelled"), payment.cancelled_at),
        ]
        return format_html_join(
            "",
            "<div>{}: {}</div>",
            ((label, f"{when:%Y-%m-%d %H:%M}") for label, when in fields if when),
        )

    @display(description=_("ledger entries"))
    def entries_list(self, payment):
        lines = JournalLine.objects.filter(entry__payment=payment).select_related(
            "entry", "account"
        )
        return format_html(
            "<table>{}</table>",
            format_html_join(
                "",
                "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>",
                (
                    (
                        line.entry.kind,
                        line.account,
                        amount(line.debit_minor, line.account.currency) if line.debit_minor else "",
                        amount(line.credit_minor, line.account.currency)
                        if line.credit_minor
                        else "",
                    )
                    for line in lines.order_by("entry__created_at", "id")
                ),
            ),
        )

    # Finance dashboard and exports ---------------------------------------------------------------

    def get_urls(self):
        view = self.admin_site.admin_view
        return [
            path("finance/", view(self.finance_view), name="payments_finance"),
            path("export/<str:what>/", view(self.export_view), name="payments_export"),
            *super().get_urls(),
        ]

    def finance_view(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied
        rows = []
        for row in selectors.dashboard():
            c = row["currency"]
            rows.append(
                {
                    "currency": c,
                    "cells": [
                        (_("Cash at the providers"), amount(row["cash"], c)),
                        (_("Held (escrow)"), amount(row["escrow"], c)),
                        (_("Owed to the sellers"), amount(row["sellers_available"], c)),
                        (_("Payouts in progress"), amount(row["payouts_in_progress"], c)),
                        (_("Refunds in progress"), amount(row["refunds_in_progress"], c)),
                        (_("Commissions"), amount(row["commissions"], c)),
                        (_("Buyer protection"), amount(row["buyer_protection"], c)),
                        (_("Payment fees"), amount(row["payment_fees"], c)),
                    ],
                    "open_disputes": row["open_disputes"],
                    "refunds_to_do": row["refunds_to_do"],
                }
            )
        context = {
            **self.admin_site.each_context(request),
            "title": _("Finance"),
            "opts": self.model._meta,
            "rows": rows,
            "balanced": ledger.is_balanced(),
            "year": timezone.now().year,
            "last_runs": ReconciliationRun.objects.all()[:5],
        }
        return TemplateResponse(request, "admin/payments/finance.html", context)

    def export_view(self, request, what):
        if not self.has_view_permission(request):
            raise PermissionDenied
        record("payments.export", None, actor=request.user, metadata={"what": what})
        if what == "payments":
            return _csv(
                "payments.csv",
                [
                    "reference",
                    "created_at",
                    "status",
                    "currency",
                    "items_minor",
                    "delivery_minor",
                    "buyer_fee_minor",
                    "commission_minor",
                    "total_minor",
                    "refunded_minor",
                    "provider",
                    "provider_reference",
                    "seller_id",
                    "buyer_id",
                ],
                (
                    [
                        p.reference,
                        p.created_at.isoformat(),
                        p.status,
                        p.currency,
                        p.items_minor,
                        p.delivery_minor,
                        p.buyer_fee_minor,
                        p.commission_minor,
                        p.total_minor,
                        p.refunded_minor,
                        p.provider,
                        p.provider_reference,
                        p.seller_id,
                        p.buyer_id,
                    ]
                    for p in Payment.objects.order_by("created_at").iterator()
                ),
            )
        if what == "ledger":
            return _csv(
                "ledger.csv",
                ["date", "entry", "key", "account", "currency", "owner_id", "debit", "credit"],
                (
                    [
                        line.entry.created_at.isoformat(),
                        line.entry.kind,
                        line.entry.idempotency_key,
                        line.account.kind,
                        line.account.currency,
                        line.account.owner_id or "",
                        line.debit_minor,
                        line.credit_minor,
                    ]
                    for line in JournalLine.objects.select_related("entry", "account")
                    .order_by("entry__created_at", "id")
                    .iterator()
                ),
            )
        if what == "payouts":
            return _csv(
                "payouts.csv",
                ["created_at", "seller_id", "amount_minor", "currency", "status", "paid_at"],
                (
                    [
                        p.created_at.isoformat(),
                        p.seller_id,
                        p.amount_minor,
                        p.currency,
                        p.status,
                        p.paid_at.isoformat() if p.paid_at else "",
                    ]
                    for p in Payout.objects.order_by("created_at").iterator()
                ),
            )
        if what == "dac7":
            if not request.user.has_perm("payments.view_sellertaxprofile"):
                raise PermissionDenied
            year = int(request.GET.get("year") or timezone.now().year)
            rows = tax.dac7_rows(year)
            header = list(rows[0]) if rows else ["seller_id"]
            return _csv(f"dac7-{year}.csv", header, ([row[k] for k in header] for row in rows))
        raise PermissionDenied


# --- Disputes ------------------------------------------------------------------------------------


class EvidenceInline(TabularInline):
    model = DisputeEvidence
    fields = ["created_at", "author", "text", "picture"]
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    @display(description=_("picture"))
    def picture(self, evidence):
        from apps.core.media.services import variant_url

        if not evidence.media_id:
            return ""
        url = variant_url(evidence.media, "medium") or variant_url(evidence.media, "thumb")
        return format_html('<img src="{}" style="max-height:120px;border-radius:8px">', url or "")


class PartialRefundForm(forms.Form):
    refund_minor = forms.IntegerField(label=_("Amount to refund"), min_value=1)
    note = forms.CharField(label=_("Note for both parties"), required=False, widget=forms.Textarea)


@admin.register(Dispute)
class DisputeAdmin(ReadOnlyAdmin):
    list_display = ["payment", "reason", "status", "response_due_at", "overdue", "decision"]
    list_filter = ["status", "reason", "overdue", "decision"]
    search_fields = ["payment__reference"]
    ordering = ["status", "-overdue", "response_due_at"]
    inlines = [EvidenceInline]
    readonly_fields = [
        "payment_link",
        "reason",
        "description",
        "opened_by",
        "response_due_at",
        "overdue",
        "room",
        "status",
        "decision",
        "refund_minor",
        "decided_by",
        "decided_at",
        "note",
    ]
    fields = readonly_fields
    actions_detail = ["release_detail", "refund_detail", "partial_detail"]

    def has_decide_dispute_permission(self, request, object_id=None):
        return request.user.has_perm("payments.decide_dispute")

    @display(description=_("payment"))
    def payment_link(self, dispute):
        url = reverse("admin:payments_payment_change", args=[dispute.payment_id])
        payment = dispute.payment
        return format_html(
            '<a href="{}">{}</a> — {}',
            url,
            payment.reference,
            amount(payment.total_minor, payment.currency),
        )

    @display(description=_("dispute room"))
    def room(self, dispute):
        if not dispute.conversation_id:
            return "—"
        url = reverse("admin:messaging_conversation_change", args=[dispute.conversation_id])
        return format_html('<a href="{}">{}</a>', url, _("Read the dispute room"))

    def _decide(self, request, object_id, decision, refund_minor=0, note=""):
        dispute = get_object_or_404(Dispute, pk=object_id)
        try:
            services.decide(
                dispute, actor=request.user, decision=decision, refund_minor=refund_minor, note=note
            )
        except DomainError as exc:
            self.message_user(request, str(exc), messages.ERROR)
        else:
            self.message_user(
                request, _("Decision recorded; both parties are told."), messages.SUCCESS
            )
        return redirect(reverse("admin:payments_dispute_change", args=[object_id]))

    @action(
        description=_("Pay the seller"),
        url_path="release",
        icon="payments",
        permissions=["decide_dispute"],
    )
    def release_detail(self, request, object_id):
        return self._decide(request, object_id, Dispute.Decision.RELEASE)

    @action(
        description=_("Refund everything"),
        url_path="refund",
        icon="undo",
        permissions=["decide_dispute"],
    )
    def refund_detail(self, request, object_id):
        return self._decide(request, object_id, Dispute.Decision.REFUND)

    @action(
        description=_("Refund part"),
        url_path="partial",
        icon="price_change",
        permissions=["decide_dispute"],
    )
    def partial_detail(self, request, object_id):
        dispute = get_object_or_404(Dispute, pk=object_id)
        form = PartialRefundForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            return self._decide(
                request,
                object_id,
                Dispute.Decision.PARTIAL,
                refund_minor=form.cleaned_data["refund_minor"],
                note=form.cleaned_data["note"],
            )
        payment = dispute.payment
        context = {
            **self.admin_site.each_context(request),
            "title": _("Refund part of %(reference)s") % {"reference": payment.reference},
            "opts": self.model._meta,
            "form": form,
            "dispute": dispute,
            "seller_amount": amount(payment.seller_gross_minor, payment.currency),
            "currency": payment.currency,
        }
        return TemplateResponse(request, "admin/payments/partial_refund.html", context)


# --- Refunds, payouts, events --------------------------------------------------------------------


@admin.register(Refund)
class RefundAdmin(ReadOnlyAdmin):
    list_display = ["payment", "created_at", "money", "status", "reason", "error"]
    list_filter = ["status", "currency", "reason"]
    search_fields = ["payment__reference", "provider_reference"]
    readonly_fields = [
        "payment",
        "amount_minor",
        "currency",
        "status",
        "reason",
        "provider_reference",
        "error",
        "completed_at",
    ]
    fields = readonly_fields
    actions = ["mark_done"]

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("payments.change_refund")

    @display(description=_("amount"))
    def money(self, refund):
        return amount(refund.amount_minor, refund.currency)

    @admin.action(description=_("Mark as done at the provider (by hand)"))
    def mark_done(self, request, queryset):
        done = 0
        for refund in queryset.filter(status__in=[Refund.Status.MANUAL, Refund.Status.FAILED]):
            services.mark_done_by_hand(refund, actor=request.user)
            done += 1
        self.message_user(request, _("Refunds closed: %(count)s") % {"count": done})


@admin.register(Payout)
class PayoutAdmin(ReadOnlyAdmin):
    list_display = ["created_at", "seller", "money", "status", "destination", "paid_at"]
    list_filter = ["status", "currency", "provider"]
    search_fields = ["seller__phone", "seller__email", "provider_reference"]

    @display(description=_("amount"))
    def money(self, payout):
        return amount(payout.amount_minor, payout.currency)


@admin.register(WebhookEvent)
class WebhookEventAdmin(ReadOnlyAdmin):
    list_display = ["created_at", "provider", "kind", "status", "error"]
    list_filter = ["provider", "status", "kind"]
    search_fields = ["event_id"]


class ReconciliationItemInline(TabularInline):
    model = ReconciliationItem
    fields = ["kind", "reference", "expected_minor", "actual_minor", "currency"]
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ReconciliationRun)
class ReconciliationRunAdmin(ReadOnlyAdmin):
    list_display = ["created_at", "provider", "checked", "discrepancies"]
    list_filter = ["provider"]
    inlines = [ReconciliationItemInline]


# --- Rules and tax data --------------------------------------------------------------------------


@admin.register(PricingRule)
class PricingRuleAdmin(AuditedModelAdmin):
    list_display = [
        "name",
        "kind",
        "is_active",
        "percent_bps",
        "fixed_minor",
        "currency",
        "country",
        "category",
        "seller",
        "valid_from",
        "valid_until",
    ]
    list_filter = ["kind", "is_active", "country", "currency"]
    search_fields = ["name", "category"]
    autocomplete_fields = ["seller"]


@admin.register(SellerTaxProfile)
class SellerTaxProfileAdmin(ReadOnlyAdmin):
    list_display = ["legal_name", "seller", "country", "is_business", "tax_id_hint"]
    list_filter = ["country", "is_business"]
    search_fields = ["legal_name", "seller__phone", "seller__email"]
    exclude = ["tax_id_secret"]
