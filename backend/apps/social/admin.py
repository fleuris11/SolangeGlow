from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from apps.core.audit.admin import AuditedModelAdmin
from apps.moderation.services import REMOVED, VISIBLE, set_visibility

from .models import ClientRating, Comment, Post, PostMedia, Review, Story

VISIBILITY_LABELS = {"visible": "success", "held": "warning", "removed": "danger"}


class VisibilityActions:
    actions = ["hide_selected", "show_selected"]

    @admin.action(description=_("Remove the selected items"))
    def hide_selected(self, request, queryset):
        for item in queryset:
            set_visibility(item, REMOVED)
        self.message_user(request, _("Removed."), messages.SUCCESS)

    @admin.action(description=_("Show the selected items again"))
    def show_selected(self, request, queryset):
        for item in queryset:
            set_visibility(item, VISIBLE)
        self.message_user(request, _("Visible again."), messages.SUCCESS)


class PostMediaInline(TabularInline):
    model = PostMedia
    fields = ["media", "role", "position"]
    readonly_fields = ["media"]
    extra = 0
    tab = True


@admin.register(Post)
class PostAdmin(VisibilityActions, AuditedModelAdmin):
    list_display = [
        "__str__",
        "author",
        "kind",
        "status",
        "visibility_badge",
        "city",
        "like_count",
        "comment_count",
        "published_at",
    ]
    list_filter = ["status", "visibility", "kind", "trade", "city"]
    search_fields = ["caption", "author__first_name", "author__phone", "city"]
    readonly_fields = [
        "author",
        "pro",
        "like_count",
        "comment_count",
        "save_count",
        "share_count",
        "published_at",
    ]
    exclude = ["location"]
    inlines = [PostMediaInline]

    @display(description=_("moderation"), ordering="visibility", label=VISIBILITY_LABELS)
    def visibility_badge(self, post):
        return post.visibility, post.get_visibility_display()


@admin.register(Comment)
class CommentAdmin(VisibilityActions, AuditedModelAdmin):
    list_display = ["text", "author", "post", "visibility", "created_at"]
    list_filter = ["visibility"]
    search_fields = ["text", "author__first_name"]
    readonly_fields = ["post", "author", "parent"]


@admin.register(Story)
class StoryAdmin(VisibilityActions, AuditedModelAdmin):
    list_display = ["author", "kind", "text", "visibility", "expires_at"]
    list_filter = ["kind", "visibility"]
    readonly_fields = ["author", "pro", "media"]


@admin.register(Review)
class ReviewAdmin(VisibilityActions, AuditedModelAdmin):
    list_display = ["pro", "rating", "author", "visibility", "replied_at", "created_at"]
    list_filter = ["rating", "visibility", "source_type"]
    search_fields = ["text", "pro__business_name", "author__first_name"]
    readonly_fields = ["author", "pro", "source_type", "source_id", "photo", "voice", "replied_at"]

    def has_add_permission(self, request):
        return False  # only from a finished booking or order


@admin.register(ClientRating)
class ClientRatingAdmin(ModelAdmin):
    list_display = ["client", "pro", "rating", "no_show", "created_at"]
    list_filter = ["no_show", "rating"]
    readonly_fields = ["pro", "client", "source_type", "source_id", "rating", "no_show", "note"]

    def has_add_permission(self, request):
        return False
