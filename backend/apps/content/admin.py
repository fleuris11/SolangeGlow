"""Contents in the back office: pages, home banners, FAQ (translated fr/en/sk, every save
is a version that can be brought back), and the tickets of the help center."""

from __future__ import annotations

from django import forms
from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TabbedTranslationAdmin
from unfold import widgets
from unfold.decorators import action

from apps.core.audit.admin import AuditedModelAdmin
from apps.core.media.services import create_asset

from .models import Banner, ContentVersion, FaqItem, Page, Ticket
from .services import help as help_services
from .services import versions


class VersionedAdmin(AuditedModelAdmin):
    """Every save is a version; « Versions » shows them and brings one back."""

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        versions.snapshot(obj, author=request.user)

    @action(description=_("Versions"), url_path="versions", icon="history")
    def versions_detail(self, request, object_id):
        obj = get_object_or_404(self.model, pk=object_id)
        meta = self.model._meta
        back = reverse(f"admin:{meta.app_label}_{meta.model_name}_change", args=[object_id])
        if request.method == "POST":
            chosen = get_object_or_404(
                ContentVersion, pk=request.POST.get("version"), object_id=str(obj.pk)
            )
            versions.restore(chosen, actor=request.user)
            self.message_user(
                request, _("Version %(number)s brought back.") % {"number": chosen.number}
            )
            return redirect(back)
        rows = [
            {
                "version": row,
                "lines": [
                    (name, str(value)[:160])
                    for name, value in row.data.items()
                    if name.endswith(("_fr", "_en", "_sk")) and value
                ][:8],
            }
            for row in versions.history(obj)[:30]
        ]
        context = {
            **self.admin_site.each_context(request),
            "title": _("Versions of %(name)s") % {"name": obj},
            "opts": meta,
            "rows": rows,
            "back": back,
        }
        return TemplateResponse(request, "admin/content/versions.html", context)


@admin.register(Page)
class PageAdmin(VersionedAdmin, TabbedTranslationAdmin):
    list_display = ["title", "slug", "kind", "is_published", "version", "updated_at"]
    list_filter = ["kind", "is_published"]
    search_fields = ["title", "slug", "body"]
    prepopulated_fields = {"slug": ["title"]}
    actions_detail = ["versions_detail"]


class BannerForm(forms.ModelForm):
    upload = forms.ImageField(label=_("new picture"), required=False)

    class Meta:
        model = Banner
        fields = [
            "title",
            "text",
            "cta",
            "link",
            "countries",
            "starts_at",
            "ends_at",
            "position",
            "is_active",
        ]


@admin.register(Banner)
class BannerAdmin(VersionedAdmin, TabbedTranslationAdmin):
    form = BannerForm
    list_display = ["title", "starts_at", "ends_at", "countries", "position", "is_active"]
    list_filter = ["is_active"]
    list_editable = ["position", "is_active"]
    search_fields = ["title", "text"]
    actions_detail = ["versions_detail"]

    def save_model(self, request, obj, form, change):
        upload = form.cleaned_data.get("upload")
        if upload:
            obj.image = create_asset(
                owner=request.user, uploaded=upload, purpose="content_banner", kind="image"
            )
        super().save_model(request, obj, form, change)


@admin.register(FaqItem)
class FaqItemAdmin(VersionedAdmin, TabbedTranslationAdmin):
    list_display = ["question", "topic", "position", "is_published", "version"]
    list_filter = ["topic", "is_published"]
    list_editable = ["position", "is_published"]
    search_fields = ["question", "answer"]
    actions_detail = ["versions_detail"]


class AnswerForm(forms.Form):
    answer = forms.CharField(
        label=_("Answer"), widget=widgets.UnfoldAdminTextareaWidget(attrs={"rows": 8})
    )


@admin.register(Ticket)
class TicketAdmin(AuditedModelAdmin):
    list_display = ["reference", "created_at", "name", "topic", "status", "answered_by"]
    list_filter = ["status", "topic", "language"]
    search_fields = ["reference", "name", "email", "phone", "message"]
    readonly_fields = [
        "reference",
        "user",
        "name",
        "email",
        "phone",
        "topic",
        "language",
        "message",
        "answer",
        "answered_at",
        "answered_by",
    ]
    fields = [*readonly_fields, "status"]
    actions_detail = ["answer_detail"]

    def has_add_permission(self, request):
        return False

    @action(description=_("Answer"), url_path="answer", icon="reply")
    def answer_detail(self, request, object_id):
        ticket = get_object_or_404(Ticket, pk=object_id)
        form = AnswerForm(request.POST or None, initial={"answer": ticket.answer})
        if request.method == "POST" and form.is_valid():
            help_services.answer(ticket, form.cleaned_data["answer"], actor=request.user)
            self.message_user(request, _("Answer sent."), messages.SUCCESS)
            return redirect(reverse("admin:content_ticket_change", args=[object_id]))
        context = {
            **self.admin_site.each_context(request),
            "title": _("Answer %(reference)s") % {"reference": ticket.reference},
            "opts": self.model._meta,
            "form": form,
            "ticket": ticket,
        }
        return TemplateResponse(request, "admin/content/answer.html", context)
