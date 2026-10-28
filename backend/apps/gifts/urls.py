from django.urls import path

from . import views

OPEN = "gifts/open/<str:token>"

urlpatterns = [
    path("gifts/ideas", views.IdeasView.as_view(), name="gifts-ideas"),
    path("gifts/quote", views.QuoteView.as_view(), name="gifts-quote"),
    path(
        "gifts/products/<uuid:variant_id>/options",
        views.ProductOptionsView.as_view(),
        name="gifts-product-options",
    ),
    path("gifts", views.SentView.as_view(), name="gifts-sent"),
    path("gifts/received", views.ReceivedView.as_view(), name="gifts-received"),
    path("gifts/cards/pay", views.CardPayView.as_view(), name="gifts-card-pay"),
    path("gifts/cards/check", views.CardCheckView.as_view(), name="gifts-card-check"),
    path("gifts/<uuid:gift_id>", views.SentGiftView.as_view(), name="gifts-sent-detail"),
    path("gifts/<uuid:gift_id>/pay", views.PayView.as_view(), name="gifts-pay"),
    path("gifts/<uuid:gift_id>/cancel", views.CancelView.as_view(), name="gifts-cancel"),
    path("gifts/<uuid:gift_id>/resend", views.ResendView.as_view(), name="gifts-resend"),
    path(OPEN, views.ReceptionView.as_view(), name="gifts-open"),
    path(f"{OPEN}/claim", views.ClaimView.as_view(), name="gifts-claim"),
    path(f"{OPEN}/book", views.BookView.as_view(), name="gifts-book"),
    path(f"{OPEN}/receive", views.ReceiveView.as_view(), name="gifts-receive"),
    path(f"{OPEN}/as-card", views.AsCardView.as_view(), name="gifts-as-card"),
    path(f"{OPEN}/photos", views.PhotoView.as_view(), name="gifts-photo"),
    path(f"{OPEN}/proof", views.ProofView.as_view(), name="gifts-proof"),
]
