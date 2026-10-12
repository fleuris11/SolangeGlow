from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display

from apps.core.media.services import variant_url

from . import services
from .models import Block, ModerationCase, Report, Sanction


class ReportInline(TabularInline):
    model = Report
    fields = ["reporter", "reason", "comment", "created_at"]
    readonly_fields = fields
    extra = 0
    can_delete = False
    tab = True

    def has_add_permission(self, request, obj=None):
        return False


def _thumbnails(target) -> str:
    items = getattr(target, "media_items", None)
    assets = [item.media for item in items.all()] if items is not None else []
    for field in ("media", "photo"):
        single = getattr(target, field, None)
        if single is not None and hasattr(single, "variants"):
            assets.append(single)
    urls = [
        variant_url(asset, "thumb") or variant_url(asset, "poster_thumb") for asset in assets[:4]
    ]
    return format_html_join(
        "",
        '<img src="{}" alt="" style="width:72px;height:72px;object-fit:cover;border-radius:8px;'
        'margin-right:6px">',
        ((url,) for url in urls if url),
    )


@admin.register(ModerationCase)
class ModerationCaseAdmin(ModelAdmin):
    """The moderation queue: reported or automatically flagged contents, one click to decide."""

    list_display = [
        "content",
        "kind",
        "author",
        "status_badge",
        "source",
        "report_count",
        "labels_list",
        "created_at",
    ]
    list_filter = ["status", "source", "hidden_until_review", "target_type"]
    search_fields = ["excerpt", "author__first_name", "author__phone", "author__email"]
    ordering = ["status", "-report_count", "created_at"]
    list_per_page = 30
    readonly_fields = [
        "preview",
        "target_link",
        "author",
        "source",
        "labels",
        "provider",
        "report_count",
        "hidden_until_review",
        "status",
        "decided_by",
        "decided_at",
    ]
    fields = [
        "preview",
        "target_link",
        "author",
        "source",
        "labels",
        "provider",
        "report_count",
        "hidden_until_review",
        "status",
        "note",
        "decided_by",
        "decided_at",
    ]
    inlines = [ReportInline]
    actions_row = ["keep_row", "remove_row", "remove_and_sanction_row"]
    actions_detail = ["keep_row", "remove_row", "remove_and_sanction_row"]
    actions = ["keep_selected", "remove_selected"]

    def has_add_permission(self, request):
        return False

    @display(description=_("content"))
    def content(self, case):
        return format_html(
            "{}<div>{}</div>", _thumbnails(case.target) if case.target else "", case.excerpt[:120]
        )

    @display(description=_("type"))
    def kind(self, case):
        return case.target_type.model_class()._meta.verbose_name

    @display(
        description=_("status"),
        label={"pending": "warning", "kept": "success", "removed": "danger"},
    )
    def status_badge(self, case):
        return case.status, case.get_status_display()

    @display(description=_("detected"))
    def labels_list(self, case):
        return ", ".join(case.labels)

    @display(description=_("preview"))
    def preview(self, case):
        target = case.target
        if target is None:
            return _("This content does not exist any more.")
        return format_html("<p>{}</p><div>{}</div>", case.excerpt, _thumbnails(target))

    @display(description=_("open the content"))
    def target_link(self, case):
        model = case.target_type
        try:
            url = reverse(f"admin:{model.app_label}_{model.model}_change", args=[case.target_id])
        except NoReverseMatch:
            return "-"
        return format_html('<a href="{}">{}</a>', url, _("Open in the admin"))

    def _decide(self, request, object_id, *, keep, sanction=False):
        case = get_object_or_404(ModerationCase, pk=object_id)
        if case.status != ModerationCase.Status.PENDING:
            self.message_user(request, _("This case was already decided."), messages.WARNING)
        else:
            services.decide(case, actor=request.user, keep=keep, sanction=sanction, note=case.note)
            self.message_user(
                request,
                _("Kept.") if keep else _("Removed. The author was told."),
                messages.SUCCESS,
            )
        return redirect(reverse("admin:moderation_moderationcase_changelist"))

    @action(description=_("Keep"), url_path="keep", icon="check_circle")
    def keep_row(self, request, object_id):
        return self._decide(request, object_id, keep=True)

    @action(description=_("Remove"), url_path="remove", icon="delete")
    def remove_row(self, request, object_id):
        return self._decide(request, object_id, keep=False)

    @action(description=_("Remove and sanction the author"), url_path="sanction", icon="gavel")
    def remove_and_sanction_row(self, request, object_id):
        return self._decide(request, object_id, keep=False, sanction=True)

    @admin.action(description=_("Keep the selected contents"))
    def keep_selected(self, request, queryset):
        for case in queryset.filter(status=ModerationCase.Status.PENDING):
            services.decide(case, actor=request.user, keep=True)

    @admin.action(description=_("Remove the selected contents"))
    def remove_selected(self, request, queryset):
        for case in queryset.filter(status=ModerationCase.Status.PENDING):
            services.decide(case, actor=request.user, keep=False)


@admin.register(Sanction)
class SanctionAdmin(ModelAdmin):
    list_display = ["user", "level", "until", "decided_by", "created_at"]
    list_filter = ["level"]
    search_fields = ["user__first_name", "user__phone", "user__email"]
    readonly_fields = ["user", "level", "until", "reason", "case", "decided_by", "created_at"]

    def has_add_permission(self, request):
        return False


@admin.register(Report)
class ReportAdmin(ModelAdmin):
    list_display = ["reason", "reporter", "target_type", "created_at"]
    list_filter = ["reason", "target_type"]
    readonly_fields = ["reporter", "reason", "comment", "target_type", "target_id", "case"]

    def has_add_permission(self, request):
        return False


@admin.register(Block)
class BlockAdmin(ModelAdmin):
    list_display = ["blocker", "blocked", "created_at"]
    search_fields = ["blocker__first_name", "blocked__first_name"]
    readonly_fields = ["blocker", "blocked"]

    def has_add_permission(self, request):
        return False
