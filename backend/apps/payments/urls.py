from django.conf import settings
from django.urls import path

from . import views

P = "payments/<uuid:payment_id>"

urlpatterns = [
    path("payments", views.PaymentListView.as_view(), name="payments"),
    path(P, views.PaymentView.as_view(), name="payment"),
    path(f"{P}/checkout", views.CheckoutView.as_view(), name="payment-checkout"),
    path(f"{P}/ship", views.ShipView.as_view(), name="payment-ship"),
    path(f"{P}/delivered", views.DeliveredView.as_view(), name="payment-delivered"),
    path(f"{P}/confirm", views.ConfirmView.as_view(), name="payment-confirm"),
    path(f"{P}/courier-link", views.CourierLinkView.as_view(), name="payment-courier-link"),
    path(f"{P}/cancel", views.CancelView.as_view(), name="payment-cancel"),
    path(f"{P}/new-code", views.NewCodeView.as_view(), name="payment-new-code"),
    path(f"{P}/dispute", views.DisputeView.as_view(), name="payment-dispute"),
    path(f"{P}/dispute/evidence", views.EvidenceView.as_view(), name="payment-evidence"),
    path("payments/courier/<str:token>", views.CourierView.as_view(), name="payment-courier"),
    path("payments/webhooks/<slug:provider>", views.webhook_view, name="payment-webhook"),
    path("me/wallet", views.WalletView.as_view(), name="wallet"),
    path("me/wallet/history", views.WalletHistoryView.as_view(), name="wallet-history"),
    path("me/payouts", views.PayoutRequestView.as_view(), name="payouts"),
    path("me/payout-methods", views.PayoutMethodsView.as_view(), name="payout-methods"),
    path("me/tax-profile", views.TaxProfileView.as_view(), name="tax-profile"),
]

# The test provider: its payment page and pretend orders (development and tests only).
if settings.PAYMENTS_FAKE_ENABLED:
    urlpatterns += [
        path(f"{P}/test-outcome", views.TestOutcomeView.as_view(), name="payment-test-outcome"),
        path("dev/payments", views.DemoPaymentView.as_view(), name="dev-payments"),
    ]
