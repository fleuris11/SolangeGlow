from django.urls import path

from . import views

urlpatterns = [
    path("me/billing", views.BillingView.as_view(), name="my-billing"),
    path("me/documents", views.DocumentsView.as_view(), name="my-documents"),
    path(
        "me/documents/<uuid:document_id>/credit",
        views.CreditView.as_view(),
        name="my-document-credit",
    ),
    path(
        "me/documents/<uuid:document_id>/send",
        views.SendElectronicView.as_view(),
        name="my-document-send",
    ),
    path("documents/<uuid:document_id>.pdf", views.DocumentPdfView.as_view(), name="document-pdf"),
]
