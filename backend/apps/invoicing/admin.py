"""Invoices in the back office: read only (an issued document never changes), the PDF, and
the legal details of each issuer (the platform's included)."""

from __future__ import annotations

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.decorators import display

from apps.core.audit.admin import AuditedModelAdmin
from apps.core.money import Money

from .models import Document, Issuer


@admin.register(Issuer)
class IssuerAdmin(AuditedModelAdmin):
    list_display = ["__str__", "pro", "is_platform", "registration", "vat_rate_bps"]
    list_filter = ["is_platform"]
    search_fields = ["legal_name", "registration", "pro__business_name"]
    readonly_fields = ["pro", "is_platform"]


@admin.register(Document)
class DocumentAdmin(AuditedModelAdmin):
    list_display = [
        "number",
        "kind",
        "issuer",
        "buyer_name",
        "total",
        "issued_at",
        "einvoice_status",
    ]
    list_filter = ["kind", "einvoice_status", "issuer__is_platform"]
    search_fields = ["number", "buyer_name", "issuer__legal_name"]
    date_hierarchy = "issued_at"

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields] + ["pdf"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @display(description=_("total"))
    def total(self, document):
        return Money(document.total_minor, document.currency).format("fr")

    @display(description=_("PDF"))
    def pdf(self, document):
        url = reverse("v1:document-pdf", args=[document.pk])
        return format_html('<a href="{}" target="_blank">{}</a>', url, document.number)
