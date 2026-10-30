"""The advertising network in the back office: advertisers, campaigns and their creatives,
activation and pause in one click, a preview of each placement, the figures and their
export for the advertiser, the boosts bought by the pros."""

from __future__ import annotations

import csv

from django import forms
from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import TabularInline
from unfold.decorators import action, display

from apps.core.audit.admin import AuditedModelAdmin
from apps.core.errors import DomainError
from apps.core.media.services import create_asset, variant_url
from apps.core.money import Money

from . import selectors
from .models import AdStat, Advertiser, Boost, Campaign, Creative, CreativeMedia, Placement
from .services import campaigns, common, delivery


def _money(value, currency) -> str:
    return Money(value or 0, currency).format("fr")


class ReadOnlyAdmin(AuditedModelAdmin):
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Advertiser)
class AdvertiserAdmin(AuditedModelAdmin):
    list_display = ["name", "kind", "contact_name", "phone", "email"]
    list_filter = ["kind"]
    search_fields = ["name", "contact_name", "email", "phone"]
    autocomplete_fields = ["pro"]


class CreativeInline(TabularInline):
    model = Creative
    extra = 0
    tab = True
    fields = ["edit", "name", "format", "placements", "is_active"]
    readonly_fields = ["edit"]

    @display(description=_("creative"))
    def edit(self, creative):
        if not creative.pk:
            return "—"
        url = reverse("admin:ads_creative_change", args=[creative.pk])
        return format_html('<a class="underline" href="{}">{}</a>', url, _("Open"))


class StatInline(TabularInline):
    model = AdStat
    extra = 0
    tab = True
    fields = ["day", "placement", "creative", "impressions", "clicks", "conversions"]
    readonly_fields = fields
    ordering = ["-day"]

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Campaign)
class CampaignAdmin(AuditedModelAdmin):
    list_display = [
        "name",
        "advertiser",
        "kind",
        "status",
        "starts_at",
        "ends_at",
        "priority",
        "show_price",
        "figures",
    ]
    list_filter = ["status", "kind", "pricing"]
    search_fields = ["name", "advertiser__name"]
    autocomplete_fields = ["advertiser"]
    date_hierarchy = "starts_at"
    readonly_fields = ["status", "figures"]
    fieldsets = [
        (None, {"fields": ["advertiser", "name", "kind", "status", "figures"]}),
        (
            _("When and how much"),
            {
                "fields": [
                    "starts_at",
                    "ends_at",
                    "priority",
                    "pricing",
                    "price_minor",
                    "currency",
                    "impressions_bought",
                ]
            },
        ),
        (
            _("Who sees it"),
            {"fields": ["countries", "cities", "languages", "roles", "trades", "max_per_day"]},
        ),
        (_("Notes"), {"fields": ["notes"]}),
    ]
    inlines = [CreativeInline, StatInline]
    actions = ["activate", "pause"]
    actions_detail = ["activate_detail", "pause_detail", "preview_detail", "export_detail"]

    @display(description=_("price"))
    def show_price(self, campaign):
        if campaign.pricing == Campaign.Pricing.PER_THOUSAND:
            return _("%(price)s per 1,000") % {
                "price": _money(campaign.price_minor, campaign.currency)
            }
        return _money(campaign.price_minor, campaign.currency)

    @display(description=_("impressions, clicks, conversions"))
    def figures(self, campaign):
        if not campaign.pk:
            return "—"
        found = delivery.stats_of([campaign])
        return f"{found['impressions']} / {found['clicks']} / {found['conversions']}"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        common.changed()

    def _run(self, request, campaign, step) -> bool:
        try:
            step(campaign, actor=request.user)
        except DomainError as exc:
            self.message_user(request, f"{campaign}: {exc.text()}", messages.ERROR)
            return False
        return True

    @admin.action(description=_("Start the campaigns"))
    def activate(self, request, queryset):
        done = sum(self._run(request, c, campaigns.activate) for c in queryset)
        self.message_user(request, _("%(count)s campaigns running.") % {"count": done})

    @admin.action(description=_("Pause the campaigns"))
    def pause(self, request, queryset):
        done = sum(self._run(request, c, campaigns.pause) for c in queryset)
        self.message_user(request, _("%(count)s campaigns paused.") % {"count": done})

    def _back(self, object_id):
        return redirect(reverse("admin:ads_campaign_change", args=[object_id]))

    @action(description=_("Start"), url_path="activate", icon="play_arrow")
    def activate_detail(self, request, object_id):
        if self._run(request, get_object_or_404(Campaign, pk=object_id), campaigns.activate):
            self.message_user(request, _("The campaign is running."))
        return self._back(object_id)

    @action(description=_("Pause"), url_path="pause", icon="pause")
    def pause_detail(self, request, object_id):
        if self._run(request, get_object_or_404(Campaign, pk=object_id), campaigns.pause):
            self.message_user(request, _("The campaign is paused."))
        return self._back(object_id)

    @action(description=_("Preview"), url_path="preview", icon="visibility")
    def preview_detail(self, request, object_id):
        campaign = get_object_or_404(Campaign, pk=object_id)
        shown = []
        for creative in campaign.creatives.prefetch_related("media_items__media").select_related(
            "campaign__advertiser", "pro__user", "pro__photo", "product__pro", "selection_product"
        ):
            for placement in creative.placements or []:
                if placement in Placement.values:
                    ad = selectors.ad_payload(creative, placement)
                    photo = (
                        next(iter(ad["media"]), None)
                        or (ad["pro"] or {}).get("photo")
                        or (ad["product"] or {}).get("photo")
                    )
                    shown.append(
                        {
                            "placement": Placement(placement).label,
                            "ad": ad,
                            "picture": (photo or {}).get("urls", {}).get("medium")
                            or (photo or {}).get("urls", {}).get("thumb"),
                        }
                    )
        context = {
            **self.admin_site.each_context(request),
            "title": _("Preview of %(name)s") % {"name": campaign.name},
            "opts": self.model._meta,
            "campaign": campaign,
            "shown": shown,
        }
        return TemplateResponse(request, "admin/ads/preview.html", context)

    @action(description=_("Export for the advertiser"), url_path="export", icon="download")
    def export_detail(self, request, object_id):
        campaign = get_object_or_404(Campaign, pk=object_id)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="campaign-{campaign.pk}.csv"'
        response.write("﻿")  # Excel reads the accents
        writer = csv.writer(response, delimiter=";")
        writer.writerow([_("day"), _("placement"), _("impressions"), _("clicks"), _("conversions")])
        for row in selectors.stats_rows(campaign):
            writer.writerow(
                [
                    row["day"].isoformat(),
                    Placement(row["placement"]).label,
                    row["impressions"],
                    row["clicks"],
                    row["conversions"],
                ]
            )
        return response


class CreativeForm(forms.ModelForm):
    placements = forms.MultipleChoiceField(
        label=_("placements"), choices=Placement.choices, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Creative
        fields = [
            "campaign",
            "name",
            "format",
            "placements",
            "title",
            "text",
            "cta",
            "link",
            "pro",
            "product",
            "selection_product",
            "is_active",
        ]

    def clean_link(self):
        from .services.tracking import safe_link

        link = self.cleaned_data.get("link", "")
        if not safe_link(link):
            raise forms.ValidationError(_("Write a page of the app (/…) or an https:// address."))
        return link


class MediaForm(forms.ModelForm):
    upload = forms.FileField(label=_("picture or short video"), required=False)

    class Meta:
        model = CreativeMedia
        fields = ["position"]


class MediaInline(TabularInline):
    model = CreativeMedia
    form = MediaForm
    fields = ["preview", "upload", "position"]
    readonly_fields = ["preview"]
    extra = 1

    @display(description=_("picture"))
    def preview(self, item):
        url = (
            variant_url(item.media, "thumb") or variant_url(item.media, "poster_medium")
            if item.pk and item.media_id
            else None
        )
        return format_html('<img src="{}" width="80" alt="">', url) if url else "—"


@admin.register(Creative)
class CreativeAdmin(AuditedModelAdmin):
    form = CreativeForm
    list_display = ["name", "campaign", "format", "placements", "is_active"]
    list_filter = ["format", "is_active"]
    search_fields = ["name", "campaign__name"]
    autocomplete_fields = ["campaign", "pro", "product", "selection_product"]
    inlines = [MediaInline]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        common.changed()

    def save_formset(self, request, form, formset, change):
        formset.save(commit=False)
        for media_form in formset.forms:
            data = getattr(media_form, "cleaned_data", None) or {}
            upload = data.get("upload")
            if upload:
                item = media_form.instance
                item.creative = form.instance
                kind = "video" if (upload.content_type or "").startswith("video/") else "image"
                item.media = create_asset(
                    owner=request.user, uploaded=upload, purpose="ad_media", kind=kind
                )
                item.save()
        for deleted in formset.deleted_objects:
            deleted.delete()
        common.changed()


@admin.register(Boost)
class BoostAdmin(ReadOnlyAdmin):
    list_display = ["created_at", "pro", "duration", "status", "show_price", "starts_at", "ends_at"]
    list_filter = ["status", "duration"]
    search_fields = ["pro__business_name", "pro__slug"]
    list_select_related = ["pro"]

    @display(description=_("price"))
    def show_price(self, boost):
        return _money(boost.amount_minor, boost.currency)


@admin.register(AdStat)
class AdStatAdmin(ReadOnlyAdmin):
    list_display = [
        "day",
        "campaign",
        "creative",
        "placement",
        "impressions",
        "clicks",
        "conversions",
    ]
    list_filter = ["placement", "day"]
    search_fields = ["campaign__name", "creative__name"]
    list_select_related = ["campaign", "creative"]
