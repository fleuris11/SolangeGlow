from __future__ import annotations

from collections import defaultdict

from django.utils.dateparse import parse_datetime
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.throttling import SettingRateThrottle
from apps.core.selectors import get_setting

from . import calls, errors, selectors, services
from . import serializers as s
from .models import AwayMessage, ConversationMember, QuickReply
from .payloads import conversation_payload, message_payload

PERSON_RELATED = ("user", "user__photo", "user__pro_profile", "user__pro_profile__photo")


def _before(request):
    value = request.query_params.get("before")
    return parse_datetime(value) if value else None


def _page_size() -> int:
    return int(get_setting("messaging.page_size", default=30))


def _others_by_conversation(user, conversation_ids) -> dict:
    rows = (
        ConversationMember.objects.filter(conversation_id__in=conversation_ids)
        .exclude(user=user)
        .select_related(*PERSON_RELATED)
    )
    grouped = defaultdict(list)
    for row in rows:
        grouped[row.conversation_id].append(row)
    return grouped


def _conversation_data(member, user, *, unread=None) -> dict:
    others = list(
        ConversationMember.objects.filter(conversation_id=member.conversation_id)
        .exclude(user=user)
        .select_related(*PERSON_RELATED)
    )
    last = selectors.last_messages(user, [member.conversation_id]).get(member.conversation_id)
    if unread is None:
        unread = selectors.unread_messages(member).count()
    return conversation_payload(member, others=others, last_message=last, unread=unread)


class MessagingView(APIView):
    permission_classes = [IsAuthenticated]


class ConversationsView(MessagingView):
    """Her conversations (newest first), or her message requests; « Write » to someone."""

    throttle_classes = [SettingRateThrottle]
    throttle_scope = "message_send"

    def get_throttles(self):
        return super().get_throttles() if self.request.method == "POST" else []

    @extend_schema(
        tags=["messaging"],
        operation_id="conversations_list",
        parameters=[
            OpenApiParameter("box", str, enum=["inbox", "requests"], required=False),
            OpenApiParameter("before", str, required=False),
        ],
        responses=s.ConversationPageSerializer,
    )
    def get(self, request):
        user = request.user
        services.mark_delivered(user)
        box = "requests" if request.query_params.get("box") == "requests" else "inbox"
        rows = selectors.memberships_of(user, box=box)
        before = _before(request)
        if before:
            rows = rows.filter(conversation__last_message_at__lt=before)
        size = _page_size()
        page = list(rows[: size + 1])
        more, page = len(page) > size, page[:size]
        ids = [m.conversation_id for m in page]
        others = _others_by_conversation(user, ids)
        lasts = selectors.last_messages(user, ids)
        results = [
            conversation_payload(
                m,
                others=others[m.conversation_id],
                last_message=lasts.get(m.conversation_id),
                unread=m.unread,
            )
            for m in page
        ]
        next_cursor = page[-1].conversation.last_message_at.isoformat() if more else None
        return Response({"results": results, "next": next_cursor})

    @extend_schema(
        tags=["messaging"], request=s.StartSerializer, responses={201: s.ConversationSerializer}
    )
    def post(self, request):
        data = s.StartSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        recipient = User.objects.filter(pk=data.validated_data["person_id"]).first()
        if recipient is None:
            raise errors.PersonNotFound()
        conversation = services.start_direct(request.user, recipient)
        member = selectors.membership(request.user, conversation.pk)
        return Response(_conversation_data(member, request.user), status=status.HTTP_201_CREATED)


class ConversationView(MessagingView):
    @extend_schema(tags=["messaging"], responses=s.ConversationSerializer)
    def get(self, request, conversation_id):
        member = selectors.membership(request.user, conversation_id)
        return Response(_conversation_data(member, request.user))

    @extend_schema(
        tags=["messaging"],
        request=s.ConversationUpdateSerializer,
        responses=s.ConversationSerializer,
    )
    def patch(self, request, conversation_id):
        data = s.ConversationUpdateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        member = services.set_preferences(request.user, conversation_id, **data.validated_data)
        return Response(_conversation_data(member, request.user))


class AcceptView(MessagingView):
    @extend_schema(tags=["messaging"], request=None, responses=s.ConversationSerializer)
    def post(self, request, conversation_id):
        member = services.accept_request(request.user, conversation_id)
        return Response(_conversation_data(member, request.user))


class DeclineView(MessagingView):
    @extend_schema(tags=["messaging"], request=None, responses={204: None})
    def post(self, request, conversation_id):
        services.decline_request(request.user, conversation_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MessagesView(MessagingView):
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "message_send"

    def get_throttles(self):
        return super().get_throttles() if self.request.method == "POST" else []

    @extend_schema(
        tags=["messaging"],
        parameters=[OpenApiParameter("before", str, required=False)],
        responses=s.MessagePageSerializer,
    )
    def get(self, request, conversation_id):
        member = selectors.membership(request.user, conversation_id)
        rows = selectors.visible_messages(request.user).filter(
            conversation_id=member.conversation_id
        )
        before = _before(request)
        if before:
            rows = rows.filter(created_at__lt=before)
        size = _page_size()
        page = list(rows.order_by("-created_at")[: size + 1])
        more, page = len(page) > size, page[:size]
        page.reverse()
        return Response(
            {
                "results": [message_payload(m, request.user) for m in page],
                "next": page[0].created_at.isoformat() if more and page else None,
            }
        )

    @extend_schema(
        tags=["messaging"], request=s.MessageCreateSerializer, responses={201: s.MessageSerializer}
    )
    def post(self, request, conversation_id):
        data = s.MessageCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        share = values.get("share")
        if share:
            share = {**share, "id": str(share["id"]) if share.get("id") else None}
            if share.get("starts_at"):
                share["starts_at"] = share["starts_at"].isoformat()
        message = services.send(
            request.user,
            conversation_id,
            text=values.get("text", ""),
            media_id=values.get("media_id"),
            share=share,
            client_id=values.get("client_id"),
        )
        return Response(message_payload(message, request.user), status=status.HTTP_201_CREATED)


class ReadView(MessagingView):
    @extend_schema(tags=["messaging"], request=None, responses={204: None})
    def post(self, request, conversation_id):
        services.mark_read(request.user, conversation_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MessageView(MessagingView):
    @extend_schema(tags=["messaging"], responses={204: None})
    def delete(self, request, message_id):
        services.delete_message(request.user, message_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MessageReportView(MessagingView):
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "report"

    @extend_schema(tags=["messaging"], request=s.MessageReportSerializer, responses={201: None})
    def post(self, request, message_id):
        data = s.MessageReportSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.report_message(request.user, message_id, **data.validated_data)
        return Response(status=status.HTTP_201_CREATED)


class UnreadView(MessagingView):
    @extend_schema(tags=["messaging"], responses=s.UnreadSerializer)
    def get(self, request):
        return Response(
            {
                "count": selectors.unread_conversation_count(request.user),
                "requests": selectors.request_count(request.user),
            }
        )


class QuickRepliesView(MessagingView):
    """The pro's saved answers, shown above the keyboard."""

    @extend_schema(tags=["messaging"], responses=s.QuickRepliesSerializer)
    def get(self, request):
        texts = QuickReply.objects.filter(user=request.user).values_list("text", flat=True)
        return Response({"texts": list(texts)})

    @extend_schema(
        tags=["messaging"], request=s.QuickRepliesSerializer, responses=s.QuickRepliesSerializer
    )
    def put(self, request):
        data = s.QuickRepliesSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        saved = services.save_quick_replies(request.user, data.validated_data["texts"])
        return Response({"texts": [reply.text for reply in saved]})


class AwayMessageView(MessagingView):
    """Automatic answer outside her opening hours."""

    @extend_schema(tags=["messaging"], responses=s.AwayMessageSerializer)
    def get(self, request):
        away = AwayMessage.objects.filter(user=request.user).first()
        return Response({"enabled": bool(away and away.enabled), "text": away.text if away else ""})

    @extend_schema(
        tags=["messaging"], request=s.AwayMessageSerializer, responses=s.AwayMessageSerializer
    )
    def put(self, request):
        data = s.AwayMessageSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        away = services.set_away_message(request.user, **data.validated_data)
        return Response({"enabled": away.enabled, "text": away.text})


# --- Calls ----------------------------------------------------------------------------------


class CallsView(MessagingView):
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "calls"


def _conversation(user, conversation_id):
    return selectors.membership(user, conversation_id).conversation


def _joined(user, call) -> dict:
    call.refresh_from_db()
    return {"call": calls.call_payload(call, user), "access": calls.access(user, call)}


class ConversationCallView(CallsView):
    @extend_schema(tags=["messaging"], responses=s.CallStateSerializer)
    def get(self, request, conversation_id):
        conversation = _conversation(request.user, conversation_id)
        return Response(calls.call_state(request.user, conversation))

    @extend_schema(
        tags=["messaging"], request=s.CallStartSerializer, responses=s.CallJoinSerializer
    )
    def post(self, request, conversation_id):
        data = s.CallStartSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        conversation = _conversation(request.user, conversation_id)
        call = calls.start_call(request.user, conversation, video=data.validated_data["video"])
        if call.caller_id != request.user.pk:  # a call was already going on: she joins it
            call = calls.answer(request.user, call)
        return Response(_joined(request.user, call), status=status.HTTP_201_CREATED)


class CallView(CallsView):
    @extend_schema(tags=["messaging"], responses=s.CallSerializer)
    def get(self, request, call_id):
        call = calls.get_call(request.user, call_id)
        return Response(calls.call_payload(call, request.user))


class CallAnswerView(CallsView):
    """Picks up (or comes back into a call going on)."""

    @extend_schema(tags=["messaging"], request=None, responses=s.CallJoinSerializer)
    def post(self, request, call_id):
        call = calls.answer(request.user, calls.get_call(request.user, call_id))
        return Response(_joined(request.user, call))


class CallDeclineView(CallsView):
    @extend_schema(tags=["messaging"], request=None, responses=s.CallSerializer)
    def post(self, request, call_id):
        call = calls.decline(request.user, calls.get_call(request.user, call_id))
        call.refresh_from_db()
        return Response(calls.call_payload(call, request.user))


class CallHangUpView(CallsView):
    @extend_schema(tags=["messaging"], request=None, responses=s.CallSerializer)
    def post(self, request, call_id):
        call = calls.hang_up(request.user, calls.get_call(request.user, call_id))
        call.refresh_from_db()
        return Response(calls.call_payload(call, request.user))


class CallLogView(CallsView):
    @extend_schema(
        tags=["messaging"],
        parameters=[OpenApiParameter("before", str, required=False)],
        responses=s.CallPageSerializer,
    )
    def get(self, request):
        rows = calls.call_log(request.user)
        before = _before(request)
        if before:
            rows = rows.filter(created_at__lt=before)
        page = list(rows[: _page_size() + 1])
        more = len(page) > _page_size()
        page = page[: _page_size()]
        return Response(
            {
                "results": [calls.call_payload(call, request.user) for call in page],
                "next": page[-1].created_at.isoformat() if more else None,
            }
        )
