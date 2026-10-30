from django.urls import path

from . import views

urlpatterns = [
    path("content/pages", views.PagesView.as_view(), name="content-pages"),
    path("content/pages/<slug:slug>", views.PageView.as_view(), name="content-page"),
    path("content/banners", views.BannersView.as_view(), name="content-banners"),
    path("help/faq", views.FaqView.as_view(), name="help-faq"),
    path("help/suggest", views.SuggestView.as_view(), name="help-suggest"),
    path("help/tickets", views.TicketsView.as_view(), name="help-tickets"),
]
