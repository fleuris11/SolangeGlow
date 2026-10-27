from django.urls import path, register_converter

from . import views


class KindConverter:
    regex = "training|sale"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(KindConverter, "livekind")

ROOT = "live/<livekind:kind>/<uuid:source_id>"

urlpatterns = [
    path("live/upcoming", views.UpcomingLivesView.as_view(), name="live-upcoming"),
    path("me/pro/lives/quota", views.LiveQuotaView.as_view(), name="live-quota"),
    path(ROOT, views.LiveStateView.as_view(), name="live-state"),
    path(f"{ROOT}/join", views.LiveJoinView.as_view(), name="live-join"),
    path(f"{ROOT}/start", views.LiveStartView.as_view(), name="live-start"),
    path(f"{ROOT}/end", views.LiveEndView.as_view(), name="live-end"),
    path(f"{ROOT}/questions", views.LiveQuestionsView.as_view(), name="live-questions"),
    path(
        f"{ROOT}/questions/<uuid:question_id>/answered",
        views.LiveAnsweredView.as_view(),
        name="live-answered",
    ),
    path(f"{ROOT}/hand", views.LiveHandView.as_view(), name="live-hand"),
    path(f"{ROOT}/hands/<uuid:user_id>/floor", views.LiveFloorView.as_view(), name="live-floor"),
]
