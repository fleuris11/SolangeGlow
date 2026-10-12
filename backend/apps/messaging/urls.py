from django.urls import path

from . import views

urlpatterns = [
    path("conversations", views.ConversationsView.as_view(), name="conversations"),
    path(
        "conversations/<uuid:conversation_id>",
        views.ConversationView.as_view(),
        name="conversation",
    ),
    path(
        "conversations/<uuid:conversation_id>/accept",
        views.AcceptView.as_view(),
        name="conversation-accept",
    ),
    path(
        "conversations/<uuid:conversation_id>/decline",
        views.DeclineView.as_view(),
        name="conversation-decline",
    ),
    path(
        "conversations/<uuid:conversation_id>/messages",
        views.MessagesView.as_view(),
        name="conversation-messages",
    ),
    path(
        "conversations/<uuid:conversation_id>/read",
        views.ReadView.as_view(),
        name="conversation-read",
    ),
    path("messages/<uuid:message_id>", views.MessageView.as_view(), name="message"),
    path(
        "messages/<uuid:message_id>/report",
        views.MessageReportView.as_view(),
        name="message-report",
    ),
    path("me/messaging/unread", views.UnreadView.as_view(), name="messaging-unread"),
    path("me/pro/quick-replies", views.QuickRepliesView.as_view(), name="quick-replies"),
    path("me/pro/away-message", views.AwayMessageView.as_view(), name="away-message"),
]
