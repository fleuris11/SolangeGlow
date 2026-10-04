from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.decorators import display

from apps.core.audit.services import record

from .models import MediaAsset
from .services import variant_url
from .tasks import process_media_asset


@admin.register(MediaAsset)
class MediaAssetAdmin(ModelAdmin):
    list_display = ["preview", "kind", "purpose", "status", "owner", "size_bytes", "created_at"]
    list_filter = ["kind", "status", "visibility", "purpose", ("created_at", RangeDateFilter)]
    list_filter_submit = True
    search_fields = ["purpose", "original_name", "owner__email", "owner__phone"]
    readonly_fields = [f.name for f in MediaAsset._meta.fields] + ["preview"]
    actions = ["reprocess"]

    @display(description=_("preview"))
    def preview(self, obj):
        name = "thumb" if obj.kind == MediaAsset.Kind.IMAGE else "poster_thumb"
        url = variant_url(obj, name) if obj.is_ready else None
        if not url:
            return "-"
        return format_html('<img src="{}" alt="" style="height:48px;border-radius:8px">', url)

    def has_add_permission(self, request):
        return False

    @admin.action(description=_("Process the selected media again"))
    def reprocess(self, request, queryset):
        for asset in queryset:
            asset.status = MediaAsset.Status.PENDING
            asset.save(update_fields=["status", "updated_at"])
            record("media.reprocess", asset, actor=request.user)
            process_media_asset.delay(str(asset.pk))
        self.message_user(request, _("Processing started again."), messages.SUCCESS)
