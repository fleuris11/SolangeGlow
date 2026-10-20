from django.urls import path

from . import views

urlpatterns = [
    path("me/glowpro", views.MyGlowProView.as_view(), name="my-glowpro"),
    path("me/glowpro/trial", views.TrialView.as_view(), name="glowpro-trial"),
    path("me/glowpro/subscribe", views.SubscribeView.as_view(), name="glowpro-subscribe"),
    path("me/glowpro/cancel", views.CancelView.as_view(), name="glowpro-cancel"),
    path("me/glowpro/resume", views.ResumeView.as_view(), name="glowpro-resume"),
    path("me/dashboard", views.DashboardView.as_view(), name="my-dashboard"),
    path("me/widget", views.MyWidgetView.as_view(), name="my-widget"),
    path("widget/<slug:slug>", views.PublicWidgetView.as_view(), name="widget"),
]
