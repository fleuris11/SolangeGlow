"""Contents in the back office: pages, home banners, FAQ (translated fr/en/sk, every save
is a version that can be brought back), and the tickets of the help center."""

from __future__ import annotations

from django import forms
from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TabbedTranslationAdmin
from unfold import widgets
from unfold.decorators import action, display

from apps.core.audit.admin import AuditedModelAdmin
from apps.core.errors import DomainError
from apps.core.media.services import check_upload, create_asset, variant_url
from apps.core.models import Country

from .models import Banner, ContentVersion, FaqItem, Page, Placement, Ticket
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


def safe_link(link: str) -> bool:
    """A page of the app (/explore) or an https:// address; nothing that runs a script."""
    link = (link or "").strip()
    if not link:
        return True
    if link.startswith("/"):
        return not link.startswith("//")
    return link.startswith("https://")


class BannerForm(forms.ModelForm):
    upload = forms.FileField(
        label=_("picture or short video"),
        required=False,
        help_text=_(
            "A picture (JPEG, PNG, WebP) or a short video (MP4). Wide pictures look best "
            "(16:7). It replaces the current one."
        ),
        widget=forms.ClearableFileInput(attrs={"accept": "image/*,video/mp4,video/quicktime"}),
    )
    remove_media = forms.BooleanField(label=_("remove the picture or video"), required=False)
    placements = forms.MultipleChoiceField(
        label=_("where it is shown"),
        choices=Placement.choices,
        widget=forms.CheckboxSelectMultiple,
        help_text=_("Tick one place or more."),
    )
    countries = forms.MultipleChoiceField(
        label=_("countries"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text=_("None ticked: every country."),
    )

    class Meta:
        model = Banner
        fields = [
            "title",
            "text",
            "cta",
            "link",
            "promo_code",
            "placements",
            "countries",
            "starts_at",
            "ends_at",
            "position",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["countries"].choices = [
            (country.code, country.name)
            for country in Country.objects.filter(is_active=True).order_by("name")
        ]
        self.upload_kind = None

    def clean_upload(self):
        upload = self.cleaned_data.get("upload")
        if not upload:
            return upload
        kind = "video" if (upload.content_type or "").startswith("video/") else "image"
        try:
            self.upload_kind = check_upload(upload, "content_banner", kind)
        except DomainError as error:
            raise forms.ValidationError(error.text()) from error
        return upload

    def clean_link(self):
        link = (self.cleaned_data.get("link") or "").strip()
        if not safe_link(link):
            raise forms.ValidationError(_("Write a page of the app (/…) or an https:// address."))
        return link

    def clean_promo_code(self):
        return (self.cleaned_data.get("promo_code") or "").strip().upper()

    def clean(self):
        data = super().clean()
        # The button text is translated: one field per language (cta_fr, cta_en...).
        has_button = any(value for name, value in data.items() if name.startswith("cta"))
        if has_button and not data.get("link"):
            self.add_error("link", _("A button needs a link: where does it lead?"))
        starts, ends = data.get("starts_at"), data.get("ends_at")
        if starts and ends and ends <= starts:
            self.add_error("ends_at", _("The end must come after the beginning."))
        return data


STATE_LABELS = {
    "live": _("Online"),
    "scheduled": _("Scheduled"),
    "ended": _("Ended"),
    "off": _("Switched off"),
}


@admin.register(Banner)
class BannerAdmin(VersionedAdmin, TabbedTranslationAdmin):
    """The announcements of the team: a picture or a video, a text, a button, a promo code,
    shown where and when the team chooses (home, Explore, Selection, Academy, pros)."""

    form = BannerForm
    list_display = ["preview", "title", "where", "country_list", "state_label", "position"]
    list_display_links = ["preview", "title"]
    list_filter = ["is_active"]
    list_editable = ["position"]
    search_fields = ["title", "text", "promo_code"]
    readonly_fields = ["preview_large"]
    actions = ["switch_on", "switch_off"]
    actions_detail = ["versions_detail"]
    fieldsets = (
        (_("What it says"), {"fields": ("title", "text", "promo_code")}),
        (_("Picture or video"), {"fields": ("preview_large", "upload", "remove_media")}),
        (_("Button"), {"fields": ("cta", "link")}),
        (_("Where and when"), {"fields": ("placements", "countries", "starts_at", "ends_at")}),
        (_("Order and state"), {"fields": ("position", "is_active")}),
    )

    def save_model(self, request, obj, form, change):
        upload = form.cleaned_data.get("upload")
        if upload:
            obj.image = create_asset(
                owner=request.user,
                uploaded=upload,
                purpose="content_banner",
                kind=form.upload_kind,
            )
        elif form.cleaned_data.get("remove_media"):
            obj.image = None
        super().save_model(request, obj, form, change)

    def _thumb(self, banner, width):
        if not banner.pk or not banner.image_id:
            return "—"
        media = banner.image
        if not media.is_ready:
            return _("Being prepared…")
        url = variant_url(media, "thumb") or variant_url(media, "poster_medium")
        if not url:
            return "—"
        return format_html('<img src="{}" width="{}" alt="" style="border-radius:8px">', url, width)

    @display(description=_("picture"))
    def preview(self, banner):
        return self._thumb(banner, 96)

    @display(description=_("current picture or video"))
    def preview_large(self, banner):
        return self._thumb(banner, 320)

    @display(description=_("where it is shown"))
    def where(self, banner):
        labels = dict(Placement.choices)
        names = [str(labels.get(key, key)).split(":")[0] for key in banner.placements or []]
        return ", ".join(names) or "—"

    @display(description=_("countries"))
    def country_list(self, banner):
        return ", ".join(banner.countries) if banner.countries else _("Every country")

    @display(
        description=_("state"),
        label={
            STATE_LABELS["live"]: "success",
            STATE_LABELS["scheduled"]: "info",
            STATE_LABELS["ended"]: "warning",
            STATE_LABELS["off"]: "danger",
        },
    )
    def state_label(self, banner):
        return STATE_LABELS[banner.state()]

    @admin.action(description=_("Switch on the selected announcements"))
    def switch_on(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, _("%(count)s switched on.") % {"count": count})

    @admin.action(description=_("Switch off the selected announcements"))
    def switch_off(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, _("%(count)s switched off.") % {"count": count})


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
