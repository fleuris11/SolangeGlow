from django.urls import path

from . import views

urlpatterns = [
    path("reports", views.ReportView.as_view(), name="report"),
    path("hides", views.HideView.as_view(), name="hide"),
    path("people/<uuid:user_id>/block", views.BlockView.as_view(), name="person-block"),
    path("me/blocks", views.MyBlocksView.as_view(), name="my-blocks"),
]
