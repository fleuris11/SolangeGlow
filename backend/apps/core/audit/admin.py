"""Admin base class that writes every create, change and delete in the audit journal."""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateFilter

from .models import AuditEvent
from .services import diff, record, snapshot


class AuditedModelAdmin(ModelAdmin):
    """Use instead of the Unfold ModelAdmin: admin changes are traced automatically."""

    def save_model(self, request, obj, form, change):
        before = None
        if change and obj.pk:
            before = snapshot(type(obj)._default_manager.filter(pk=obj.pk).first())
        super().save_model(request, obj, form, change)
        before, after = diff(before, snapshot(obj))
        if change and not after:
            return
        action = "admin.change" if change else "admin.create"
        record(action, obj, actor=request.user, before=before, after=after)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        many_to_many = {field.name for field in self.model._meta.many_to_many}
        changed = [name for name in form.changed_data if name in many_to_many]
        if change and changed:
            record(
                "admin.change",
                form.instance,
                actor=request.user,
                metadata={"many_to_many": changed},
            )

    def delete_model(self, request, obj):
        record("admin.delete", obj, actor=request.user, before=snapshot(obj))
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            record("admin.delete", obj, actor=request.user, before=snapshot(obj))
        super().delete_queryset(request, queryset)


@admin.register(AuditEvent)
class AuditEventAdmin(ModelAdmin):
    list_display = ["created_at", "actor", "action", "target_type", "target_repr", "ip_address"]
    list_filter = ["action", "target_type", ("created_at", RangeDateFilter)]
    list_filter_submit = True
    search_fields = ["action", "target_repr", "target_id", "actor__email", "actor__phone"]
    readonly_fields = [f.name for f in AuditEvent._meta.fields]
    fieldsets = (
        (None, {"fields": ("created_at", "actor", "action", "ip_address", "user_agent")}),
        (_("Object"), {"fields": ("target_type", "target_id", "target_repr")}),
        (_("Changes"), {"fields": ("before", "after", "metadata")}),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
