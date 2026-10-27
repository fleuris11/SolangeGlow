"""Back-office of the lives: what is on air, the numbers of each live, cutting a live,
deleting a replay, the written questions (moderated like any content)."""

from __future__ import annotations

from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from unfold.admin import TabularInline
from unfold.decorators import action, display

from apps.core.audit.admin import AuditedModelAdmin

from . import services
from .models import LiveQuestion, LiveRoom


class QuestionInline(TabularInline):
    model = LiveQuestion
    fields = ["created_at", "author", "text", "answered_at", "visibility"]
    readonly_fields = ["created_at", "author", "text", "answered_at"]
    extra = 0
    tab = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(LiveRoom)
class LiveRoomAdmin(AuditedModelAdmin):
    list_display = [
        "title",
        "kind",
        "host_name",
        "status",
        "started_at",
        "length",
        "peak_viewers",
        "total_viewers",
        "replay_status",
    ]
    list_filter = ["status", "kind", "replay_status", "country", "ended_by_staff"]
    search_fields = ["title", "pro__business_name"]
    readonly_fields = [
        "kind",
        "source_id",
        "name",
        "host",
        "pro",
        "country",
        "title",
        "status",
        "started_at",
        "ended_at",
        "ends_by",
        "max_viewers",
        "viewers",
        "peak_viewers",
        "total_viewers",
        "speaker_identity",
        "ended_by_staff",
        "replay_status",
        "replay",
        "replay_until",
    ]
    fields = readonly_fields
    inlines = [QuestionInline]
    actions_detail = ["cut_detail", "delete_replay_detail"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @display(description=_("host"))
    def host_name(self, room):
        return room.pro.display_name if room.pro_id else "Solange Glow"

    @display(description=_("length (min)"))
    def length(self, room):
        if room.started_at and room.ended_at:
            return round((room.ended_at - room.started_at).total_seconds() / 60)
        return "-"

    def _back(self, object_id):
        return redirect(reverse("admin:live_liveroom_change", args=[object_id]))

    @action(description=_("Cut the live"), url_path="cut", icon="stop_circle")
    def cut_detail(self, request, object_id):
        room = get_object_or_404(LiveRoom, pk=object_id)
        if room.status == LiveRoom.Status.ENDED:
            self.message_user(request, _("This live is already over."), messages.WARNING)
        else:
            services.end(room, by=request.user, staff=True, reason="staff")
            self.message_user(request, _("The live is cut."), messages.SUCCESS)
        return self._back(object_id)

    @action(description=_("Delete the replay"), url_path="delete-replay", icon="delete")
    def delete_replay_detail(self, request, object_id):
        room = get_object_or_404(LiveRoom, pk=object_id)
        if room.replay_status == LiveRoom.Replay.NONE:
            self.message_user(request, _("This live has no replay."), messages.WARNING)
        else:
            services.delete_replay(room, by=request.user)
            self.message_user(request, _("The replay is deleted."), messages.SUCCESS)
        return self._back(object_id)


@admin.register(LiveQuestion)
class LiveQuestionAdmin(AuditedModelAdmin):
    list_display = ["text", "author", "room", "created_at", "visibility"]
    list_filter = ["visibility"]
    search_fields = ["text"]
    readonly_fields = ["room", "author", "text", "at_second", "answered_at"]
    fields = [*readonly_fields, "visibility"]

    def has_add_permission(self, request):
        return False
