from django import forms
from django.contrib import admin, messages
from django.contrib.gis.geos import Point
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from modeltranslation.admin import TabbedTranslationAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display

from apps.core.audit.admin import AuditedModelAdmin
from apps.core.selectors import get_setting

from . import services
from .models import (
    Closure,
    OpeningPeriod,
    ProProfile,
    ProVerification,
    Service,
    Trade,
)

REVIEW_PERMISSION = "pros.review_identity"


def can_review_identity(request) -> bool:
    """Menu entry « Identity checks »: the verification team only."""
    return request.user.has_perm(REVIEW_PERMISSION)


@admin.register(Trade)
class TradeAdmin(AuditedModelAdmin, TabbedTranslationAdmin):
    list_display = ["name", "key", "icon", "position", "is_active"]
    list_editable = ["position", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["key", "name"]


class ProProfileForm(forms.ModelForm):
    """The position is edited as two numbers (copied from a map app if needed)."""

    latitude = forms.FloatField(label=_("latitude"), required=False, min_value=-90, max_value=90)
    longitude = forms.FloatField(
        label=_("longitude"), required=False, min_value=-180, max_value=180
    )

    class Meta:
        model = ProProfile
        fields = [
            "user",
            "business_name",
            "slug",
            "kind",
            "trades",
            "bio",
            "languages",
            "social_links",
            "country",
            "currency",
            "city",
            "district",
            "address",
            "receives_clients",
            "landmarks",
            "travels_to_clients",
            "service_radius_km",
            "travel_fee_minor",
            "suspension_reason",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.location is not None:
            self.fields["latitude"].initial = self.instance.location.y
            self.fields["longitude"].initial = self.instance.location.x

    def save(self, commit=True):
        latitude, longitude = self.cleaned_data.get("latitude"), self.cleaned_data.get("longitude")
        if latitude is not None and longitude is not None:
            self.instance.location = Point(longitude, latitude, srid=4326)
            self.instance.location_source = ProProfile.LocationSource.ADMIN
        return super().save(commit)


class ServiceInline(TabularInline):
    model = Service
    fields = ["name", "price_kind", "price_minor", "currency", "duration_minutes", "is_active"]
    readonly_fields = ["duration_minutes"]
    extra = 0
    show_change_link = False
    tab = True


class OpeningPeriodInline(TabularInline):
    model = OpeningPeriod
    extra = 0
    tab = True


class ClosureInline(TabularInline):
    model = Closure
    extra = 0
    tab = True


@admin.register(ProProfile)
class ProProfileAdmin(AuditedModelAdmin):
    form = ProProfileForm
    list_display = [
        "display_name_column",
        "slug_link",
        "city",
        "district",
        "status_badge",
        "verification_badge",
        "kind",
        "rating_average",
        "level",
        "published_at",
    ]
    list_filter = [
        "status",
        "verification_status",
        "level",
        "kind",
        "country",
        "trades",
        "receives_clients",
        "travels_to_clients",
        "city",
    ]
    search_fields = [
        "business_name",
        "slug",
        "city",
        "district",
        "user__first_name",
        "user__last_name",
        "user__email",
        "user__phone",
    ]
    list_per_page = 50
    autocomplete_fields = ["user"]
    filter_horizontal = ["trades"]
    readonly_fields = [
        "status",
        "published_at",
        "suspended_at",
        "verification_status",
        "verified_at",
        "rating_average",
        "rating_count",
        "created_at",
        "updated_at",
        "photo",
        "cover",
        "bio_voice",
        "itinerary_video",
        "landmarks_voice",
    ]
    inlines = [ServiceInline, OpeningPeriodInline, ClosureInline]
    actions = ["suspend_selected", "reinstate_selected"]
    actions_submit_line = ["suspend_from_form", "reinstate_from_form"]
    fieldsets = (
        (
            _("Showcase"),
            {
                "fields": (
                    "user",
                    "business_name",
                    "slug",
                    "kind",
                    "trades",
                    "bio",
                    "languages",
                    "social_links",
                )
            },
        ),
        (
            _("Place"),
            {
                "fields": (
                    "country",
                    "currency",
                    "city",
                    "district",
                    "address",
                    "latitude",
                    "longitude",
                    "receives_clients",
                    "landmarks",
                    "travels_to_clients",
                    "service_radius_km",
                    "travel_fee_minor",
                )
            },
        ),
        (
            _("Status"),
            {
                "fields": (
                    "status",
                    "published_at",
                    "suspended_at",
                    "suspension_reason",
                    "verification_status",
                    "verified_at",
                    "rating_average",
                    "rating_count",
                )
            },
        ),
        (
            _("Media"),
            {
                "classes": ["tab"],
                "fields": ("photo", "cover", "bio_voice", "itinerary_video", "landmarks_voice"),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "country")

    @display(description=_("business name"), ordering="business_name")
    def display_name_column(self, pro):
        return pro.display_name

    @display(description=_("short link"), ordering="slug")
    def slug_link(self, pro):
        if not pro.slug:
            return "-"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">/{}</a>',
            services.short_link(pro),
            pro.slug,
        )

    @display(
        description=_("status"),
        ordering="status",
        label={
            ProProfile.Status.DRAFT: "info",
            ProProfile.Status.PUBLISHED: "success",
            ProProfile.Status.SUSPENDED: "danger",
        },
    )
    def status_badge(self, pro):
        return pro.status, pro.get_status_display()

    @display(
        description=_("verification"),
        ordering="verification_status",
        label={
            ProProfile.Verification.NONE: "info",
            ProProfile.Verification.PENDING: "warning",
            ProProfile.Verification.VERIFIED: "success",
            ProProfile.Verification.REJECTED: "danger",
        },
    )
    def verification_badge(self, pro):
        return pro.verification_status, pro.get_verification_status_display()

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        services.refresh_search(obj)

    @admin.action(description=_("Suspend the selected showcases"))
    def suspend_selected(self, request, queryset):
        count = 0
        for pro in queryset.exclude(status=ProProfile.Status.SUSPENDED):
            services.suspend(
                pro,
                actor=request.user,
                reason=pro.suspension_reason or str(_("Rules not followed.")),
            )
            count += 1
        self.message_user(
            request,
            ngettext("%(n)d showcase suspended.", "%(n)d showcases suspended.", count)
            % {"n": count},
            messages.SUCCESS,
        )

    @admin.action(description=_("End the suspension of the selected showcases"))
    def reinstate_selected(self, request, queryset):
        count = 0
        for pro in queryset.filter(status=ProProfile.Status.SUSPENDED):
            services.reinstate(pro, actor=request.user)
            count += 1
        self.message_user(
            request,
            ngettext("%(n)d showcase back online.", "%(n)d showcases back online.", count)
            % {"n": count},
            messages.SUCCESS,
        )

    @action(description=_("Save and suspend (reason above)"))
    def suspend_from_form(self, request, obj):
        reason = obj.suspension_reason or str(_("Rules not followed."))
        services.suspend(obj, actor=request.user, reason=reason)
        self.message_user(request, _("The showcase is suspended."), messages.WARNING)

    @action(description=_("Save and end the suspension"))
    def reinstate_from_form(self, request, obj):
        if obj.status == ProProfile.Status.SUSPENDED:
            services.reinstate(obj, actor=request.user)
            self.message_user(request, _("The showcase is back."), messages.SUCCESS)

    # --- Map of the pros -----------------------------------------------------------

    def get_urls(self):
        return [
            path(
                "map/",
                self.admin_site.admin_view(self.map_view),
                name="pros_proprofile_map",
            ),
            *super().get_urls(),
        ]

    def map_view(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied
        points = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [pro.location.x, pro.location.y]},
                "properties": {
                    "name": pro.display_name,
                    "status": pro.status,
                    "city": pro.city,
                    "url": reverse("admin:pros_proprofile_change", args=[pro.pk]),
                },
            }
            for pro in ProProfile.objects.filter(location__isnull=False)
            .only("business_name", "status", "city", "location", "user")
            .select_related("user")
        ]
        context = {
            **self.admin_site.each_context(request),
            "title": _("Map of the pros"),
            "opts": self.model._meta,
            "points": {"type": "FeatureCollection", "features": points},
            "style_url": get_setting(
                "maps.style_url", default="https://tiles.openfreemap.org/styles/liberty"
            ),
            "attribution": get_setting("maps.attribution", default="© OpenStreetMap"),
            "count": len(points),
        }
        return TemplateResponse(request, "admin/pros/map.html", context)


class VerificationForm(forms.ModelForm):
    class Meta:
        model = ProVerification
        fields = ["rejection_reason"]


@admin.register(ProVerification)
class ProVerificationAdmin(ModelAdmin):
    """Queue of identity checks. Only the verification team sees documents."""

    form = VerificationForm
    list_display = [
        "pro",
        "document_type",
        "status_badge",
        "created_at",
        "reviewed_by",
        "reviewed_at",
    ]
    list_filter = ["status", "document_type"]
    search_fields = ["pro__business_name", "pro__slug", "pro__user__phone", "pro__user__email"]
    ordering = ["status", "created_at"]
    readonly_fields = [
        "pro",
        "document_type",
        "status",
        "created_at",
        "reviewed_by",
        "reviewed_at",
        "documents",
    ]
    fields = [
        "pro",
        "document_type",
        "status",
        "created_at",
        "documents",
        "rejection_reason",
        "reviewed_by",
        "reviewed_at",
    ]
    actions_submit_line = ["approve", "reject"]

    def has_module_permission(self, request):
        return request.user.has_perm(REVIEW_PERMISSION)

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm(REVIEW_PERMISSION)

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm(REVIEW_PERMISSION) and (
            obj is None or obj.status == ProVerification.Status.PENDING
        )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @display(
        description=_("status"),
        ordering="status",
        label={
            ProVerification.Status.PENDING: "warning",
            ProVerification.Status.APPROVED: "success",
            ProVerification.Status.REJECTED: "danger",
        },
    )
    def status_badge(self, verification):
        return verification.status, verification.get_status_display()

    @display(description=_("documents"))
    def documents(self, verification):
        if verification.pk is None:
            return "-"
        urls = [
            reverse("admin:pros_proverification_file", args=[verification.pk, which])
            for which in ("document", "selfie")
        ]
        return format_html(
            '<div style="display:flex;gap:16px;flex-wrap:wrap">'
            '<img src="{}" alt="" style="max-width:420px;border-radius:12px">'
            '<img src="{}" alt="" style="max-width:300px;border-radius:12px"></div>'
            "<p>{}</p>",
            urls[0],
            urls[1],
            _("Each opening of these pictures is written in the audit journal."),
        )

    def get_urls(self):
        return [
            path(
                "<uuid:pk>/file/<str:which>/",
                self.admin_site.admin_view(self.file_view),
                name="pros_proverification_file",
            ),
            *super().get_urls(),
        ]

    def file_view(self, request, pk, which):
        if not request.user.has_perm(REVIEW_PERMISSION) or which not in ("document", "selfie"):
            raise PermissionDenied
        verification = get_object_or_404(ProVerification, pk=pk)
        data = services.read_verification_file(verification, which, actor=request.user)
        response = HttpResponse(data, content_type="image/jpeg")
        response["Cache-Control"] = "no-store"
        response["X-Robots-Tag"] = "noindex"
        return response

    def has_review_identity_permission(self, request, object_id=None):
        # A method, not "pros.review_identity": Unfold would look the permission up in
        # the database while starting, before the first migration.
        return request.user.has_perm(REVIEW_PERMISSION)

    @action(description=_("Save and approve: verified pro"), permissions=["review_identity"])
    def approve(self, request, obj):
        services.review_verification(obj, actor=request.user, approve=True)
        self.message_user(request, _("The pro is verified."), messages.SUCCESS)

    @action(description=_("Save and refuse (reason above)"), permissions=["review_identity"])
    def reject(self, request, obj):
        if not obj.rejection_reason.strip():
            self.message_user(request, _("Write the reason of the refusal first."), messages.ERROR)
            return
        services.review_verification(
            obj, actor=request.user, approve=False, reason=obj.rejection_reason
        )
        self.message_user(request, _("The pro was told why."), messages.WARNING)
