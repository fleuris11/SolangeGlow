from django.urls import path

from . import views

urlpatterns = [
    path("notifications", views.NotificationListView.as_view(), name="notifications"),
    path(
        "notifications/unread-count", views.UnreadCountView.as_view(), name="notifications-unread"
    ),
    path("notifications/read", views.MarkReadView.as_view(), name="notifications-read"),
    path("notifications/test", views.TestNotificationView.as_view(), name="notifications-test"),
    path("notifications/push/key", views.PushKeyView.as_view(), name="push-key"),
    path(
        "notifications/push/subscriptions",
        views.PushSubscriptionView.as_view(),
        name="push-subscribe",
    ),
    path(
        "notifications/push/unsubscribe",
        views.PushUnsubscribeView.as_view(),
        name="push-unsubscribe",
    ),
]
