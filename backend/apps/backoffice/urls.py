from django.urls import path

from . import views

urlpatterns = [
    path("i18n/overrides", views.OverridesView.as_view(), name="i18n-overrides"),
    path(
        "backoffice/impersonation/stop",
        views.StopImpersonationView.as_view(),
        name="impersonation-stop",
    ),
    path("prospects/claim", views.ProspectClaimView.as_view(), name="prospects-claim"),
    path("prospects/<str:code>/stop", views.prospect_stop, name="prospects-stop"),
]
