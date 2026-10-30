from django.urls import path

from . import views

urlpatterns = [
    path("ads", views.AdsView.as_view(), name="ads"),
    path("ads/click/<str:token>", views.ClickView.as_view(), name="ads-click"),
    path("ads/boosts", views.BoostView.as_view(), name="ads-boosts"),
]
