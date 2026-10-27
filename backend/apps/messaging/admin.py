"""Private conversations are not open to the team: only after a report or in a dispute.

The list shows those conversations only; each opening of one is written in the audit
journal (who, when, why).
"""

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _
from unfold.decorators import action, display

from apps.core.audit.admin import AuditedModelAdmin
from apps.core.audit.services import record
from apps.core.errors import DomainError
from apps.moderation.models import ModerationCase

from . import calls
from .models import Call, Conversation, ConversationMember, Message


def reported_message_ids():
    return ModerationCase.objects.filter(
        target_type=ContentType.objects.get_for_model(Message)
    ).values("target_id")


def reviewable_conversations():
    """Conversations the team may read: a reported message, or a dispute room."""
    reported = Message.objects.filter(pk__in=reported_message_ids()).values("conversation_id")
    return Conversation.objects.filter(Q(purpose=Conversation.Purpose.DISPUTE) | Q(pk__in=reported))


@admin.register(Conversation)
class ConversationAdmin(AuditedModelAdmin):
    list_display = ["__str__", "kind", "purpose", "people", "last_message_at", "warning"]
    list_filter = ["kind", "purpose", "payment_warning"]
    ordering = ["-last_message_at"]
    fields = [
        "kind",
        "purpose",
        "title",
        "people",
        "reason",
        "payment_warning",
        "created_at",
        "transcript",
    ]
    readonly_fields = fields
    actions_detail = ["call_detail"]

    @action(description=_("Three-way call"), url_path="call", icon="call")
    def call_detail(self, request, object_id):
        """Starts (or joins) the audio call of a dispute room; the team member answers in
        the web app, like the buyer and the seller."""
        conversation = get_object_or_404(reviewable_conversations(), pk=object_id)
        back = reverse("admin:messaging_conversation_change", args=[object_id])
        if conversation.purpose != Conversation.Purpose.DISPUTE:
            self.message_user(request, _("Calls are only for dispute rooms."), messages.WARNING)
            return redirect(back)
        ConversationMember.objects.get_or_create(
            conversation=conversation,
            user=request.user,
            defaults={"role": ConversationMember.Role.STAFF},
        )
        try:
            call = calls.start_call(request.user, conversation, video=False)
        except DomainError as exc:
            self.message_user(request, exc.text(), messages.ERROR)
            return redirect(back)
        return redirect(f"{settings.SITE_URL}/fr/appel/{call.pk}")

    def get_queryset(self, request):
        return (
            reviewable_conversations()
            .annotate(member_count=Count("members"))
            .prefetch_related("members__user")
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def change_view(self, request, object_id, form_url="", extra_context=None):
        conversation = self.get_queryset(request).filter(pk=object_id).first()
        if conversation is not None:
            record(
                "messaging.conversation_viewed",
                conversation,
                actor=request.user,
                metadata={"reason": self._reason_key(conversation)},
            )
        return super().change_view(request, object_id, form_url, extra_context)

    @staticmethod
    def _reason_key(conversation) -> str:
        return "dispute" if conversation.purpose == Conversation.Purpose.DISPUTE else "report"

    @display(description=_("people"))
    def people(self, conversation):
        return ", ".join(str(m.user) for m in conversation.members.all())

    @display(description=_("payment warning"), boolean=True)
    def warning(self, conversation):
        return conversation.payment_warning

    @display(description=_("why it can be read"))
    def reason(self, conversation):
        if conversation.purpose == Conversation.Purpose.DISPUTE:
            return _("Dispute room")
        cases = ModerationCase.objects.filter(
            target_type=ContentType.objects.get_for_model(Message),
            target_id__in=conversation.messages.values("pk"),
        )
        return format_html_join(
            ", ",
            '<a href="{}">{}</a>',
            (
                (
                    reverse("admin:moderation_moderationcase_change", args=[case.pk]),
                    _("Report of %(date)s") % {"date": case.created_at.date().isoformat()},
                )
                for case in cases
            ),
        )

    @display(description=_("messages"))
    def transcript(self, conversation):
        reported = set(
            ModerationCase.objects.filter(
                target_type=ContentType.objects.get_for_model(Message)
            ).values_list("target_id", flat=True)
        )
        rows = conversation.messages.select_related("sender").order_by("created_at")[:500]
        return format_html(
            '<div style="display:flex;flex-direction:column;gap:8px">{}</div>',
            format_html_join(
                "",
                '<div id="m-{}" style="padding:8px;border-radius:8px;{}">'
                "<strong>{}</strong> <small>{}</small><div>{}</div></div>",
                (
                    (
                        message.pk,
                        "border:2px solid #c8102e" if message.pk in reported else "",
                        message.sender or _("Solange Glow"),
                        message.created_at.strftime("%Y-%m-%d %H:%M"),
                        _message_summary(message),
                    )
                    for message in rows
                ),
            ),
        )


def _message_summary(message: Message) -> str:
    if message.deleted_at:
        return f"[{_('deleted')}] {message.text}"
    labels = f" ⚠ {', '.join(message.fraud_labels)}" if message.fraud_labels else ""
    if message.kind == Message.Kind.SHARE:
        return f"[{message.get_share_kind_display()}] {message.share_data.get('title', '')}"
    if message.kind in (Message.Kind.PHOTO, Message.Kind.VOICE):
        return f"[{message.get_kind_display()}] {message.text}{labels}"
    return f"{message.text}{labels}"


@admin.register(Message)
class MessageAdmin(AuditedModelAdmin):
    """Only reported messages; opening one shows its conversation."""

    list_display = ["__str__", "sender", "kind", "created_at", "visibility"]
    list_filter = ["kind", "visibility"]

    def get_queryset(self, request):
        return Message.objects.filter(pk__in=reported_message_ids()).select_related("sender")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def change_view(self, request, object_id, form_url="", extra_context=None):
        message = self.get_queryset(request).filter(pk=object_id).first()
        if message is None:
            return redirect(reverse("admin:messaging_conversation_changelist"))
        url = reverse("admin:messaging_conversation_change", args=[message.conversation_id])
        return redirect(f"{url}#m-{message.pk}")


@admin.register(Call)
class CallAdmin(AuditedModelAdmin):
    """The call log: who, when, how long. Nothing of what was said."""

    list_display = ["created_at", "kind", "status", "purpose", "people", "minutes"]
    list_filter = ["kind", "status", "conversation__purpose"]
    date_hierarchy = "created_at"
    fields = [
        "conversation",
        "caller",
        "kind",
        "status",
        "people",
        "created_at",
        "answered_at",
        "ended_at",
        "minutes",
    ]
    readonly_fields = fields

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("conversation", "caller")
            .prefetch_related("participants__user")
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @display(description=_("purpose"))
    def purpose(self, call):
        return call.conversation.get_purpose_display()

    @display(description=_("people"))
    def people(self, call):
        return ", ".join(str(p.user) for p in call.participants.all())

    @display(description=_("length (min)"))
    def minutes(self, call):
        return round(call.duration_seconds / 60, 1)
