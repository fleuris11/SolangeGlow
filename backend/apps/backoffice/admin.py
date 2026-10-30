"""Prospects, corrected translations and the sign-ins as a member in the back office."""

from __future__ import annotations

from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from unfold.decorators import action, display

from apps.core.audit.admin import AuditedModelAdmin

from .models import Impersonation, Prospect, TranslationOverride
from .services import prospects, translations


@admin.register(Prospect)
class ProspectAdmin(AuditedModelAdmin):
    list_display = [
        "name",
        "business_name",
        "phone",
        "city",
        "trade",
        "status",
        "invited_at",
        "owner",
    ]
    list_filter = ["status", "country", "city", "trade", "source"]
    search_fields = ["name", "business_name", "phone", "email", "notes"]
    readonly_fields = ["invite_code", "invite_link", "invited_at", "signed_up_user"]
    fields = [
        "name",
        "business_name",
        "phone",
        "email",
        "city",
        "country",
        "trade",
        "source",
        "status",
        "notes",
        "owner",
        "invite_code",
        "invite_link",
        "invited_at",
        "signed_up_user",
    ]
    actions = ["send_invitation"]
    actions_list = ["import_list"]

    @display(description=_("sign-up link"))
    def invite_link(self, prospect):
        return prospects.link_of(prospect) if prospect.pk else "—"

    @admin.action(description=_("Send the invitation (WhatsApp, else SMS)"))
    def send_invitation(self, request, queryset):
        sent = sum(prospects.invite(p, actor=request.user) for p in queryset)
        self.message_user(
            request,
            _("%(count)s invitations sent (a prospect without a phone is skipped).")
            % {"count": sent},
            messages.SUCCESS,
        )

    @action(description=_("Import a CSV file"), url_path="import", icon="upload_file")
    def import_list(self, request):
        return redirect(reverse("admin:backoffice_prospects_import"))


@admin.register(TranslationOverride)
class TranslationOverrideAdmin(AuditedModelAdmin):
    list_display = ["key", "language", "domain", "text", "updated_by", "updated_at"]
    list_filter = ["domain", "language"]
    search_fields = ["key", "text"]
    readonly_fields = ["updated_by"]
    actions_list = ["open_search"]

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        translations.changed()

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        translations.changed()

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        translations.changed()

    @action(description=_("Search a text"), url_path="search", icon="search")
    def open_search(self, request):
        return redirect(reverse("admin:backoffice_translations"))


@admin.register(Impersonation)
class ImpersonationAdmin(AuditedModelAdmin):
    list_display = ["created_at", "staff", "target", "reason", "expires_at", "ended_at", "actions"]
    list_filter = ["staff"]
    search_fields = ["target__email", "target__phone", "staff__email", "reason"]
    readonly_fields = [f.name for f in Impersonation._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
