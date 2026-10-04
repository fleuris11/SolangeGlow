from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TabbedTranslationAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import RangeDateFilter

from apps.core.audit.admin import AuditedModelAdmin

from . import services
from .models import Notification, NotificationDelivery, NotificationTemplate, PushSubscription


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(AuditedModelAdmin, TabbedTranslationAdmin):
    list_display = ["event_key", "channel", "title", "is_active", "updated_at"]
    list_filter = ["channel", "is_active", "event_key"]
    list_editable = ["is_active"]
    search_fields = ["event_key", "title", "body"]
    actions = ["send_test_to_me"]
    fields = ["event_key", "channel", "description", "title", "body", "link", "is_active"]

    @admin.action(description=_("Send this event to me (test)"))
    def send_test_to_me(self, request, queryset):
        for event_key in set(queryset.values_list("event_key", flat=True)):
            services.notify(request.user, event_key, {"date": "", "contact": ""})
        self.message_user(request, _("Test sent to your account."), messages.SUCCESS)


class DeliveryInline(TabularInline):
    model = NotificationDelivery
    extra = 0
    max_num = 0
    can_delete = False
    fields = ["channel", "status", "scheduled_for", "attempts", "sent_at", "error"]
    readonly_fields = fields


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ["created_at", "user", "event_key", "title", "in_app", "read_at"]
    list_filter = ["event_key", "in_app", ("created_at", RangeDateFilter)]
    list_filter_submit = True
    search_fields = ["user__email", "user__phone", "event_key", "title"]
    readonly_fields = [f.name for f in Notification._meta.fields]
    inlines = [DeliveryInline]

    def has_add_permission(self, request):
        return False


@admin.register(PushSubscription)
class PushSubscriptionAdmin(ModelAdmin):
    list_display = ["user", "user_agent", "last_used_at", "created_at"]
    search_fields = ["user__email", "user__phone"]
    readonly_fields = ["user", "user_agent", "last_used_at", "created_at"]
    exclude = ["endpoint", "p256dh", "auth"]

    def has_add_permission(self, request):
        return False
