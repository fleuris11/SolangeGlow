from django.urls import path

from . import views

S = "me/salon"

urlpatterns = [
    # Packages and installments.
    path(f"{S}/packages", views.PackagesView.as_view(), name="salon-packages"),
    path(f"{S}/packages/<uuid:package_id>", views.PackageView.as_view(), name="salon-package"),
    path(f"{S}/sold/<uuid:sold_id>/use", views.SessionUseView.as_view(), name="salon-session-use"),
    path(
        f"{S}/installments/<uuid:installment_id>/record",
        views.InstallmentRecordView.as_view(),
        name="salon-installment-record",
    ),
    # The complete client file.
    path(f"{S}/clients/<uuid:record_id>", views.ClientFileView.as_view(), name="salon-client"),
    path(
        f"{S}/clients/<uuid:record_id>/packages",
        views.SellPackageView.as_view(),
        name="salon-client-package",
    ),
    # Gift cards.
    path(f"{S}/gift-cards", views.GiftCardsView.as_view(), name="salon-gift-cards"),
    path(f"{S}/gift-cards/check", views.GiftCardCheckView.as_view(), name="salon-gift-card-check"),
    path(
        f"{S}/gift-cards/redeem", views.GiftCardRedeemView.as_view(), name="salon-gift-card-redeem"
    ),
    # Stock.
    path(f"{S}/stock", views.StockView.as_view(), name="salon-stock"),
    path(f"{S}/stock/ean/<str:ean>", views.StockBarcodeView.as_view(), name="salon-stock-ean"),
    path(f"{S}/stock/<uuid:item_id>", views.StockItemView.as_view(), name="salon-stock-item"),
    path(f"{S}/stock/<uuid:item_id>/move", views.StockMoveView.as_view(), name="salon-stock-move"),
    path(
        f"{S}/stock/<uuid:item_id>/count", views.StockCountView.as_view(), name="salon-stock-count"
    ),
    path(
        f"{S}/services/<uuid:service_id>/consumption",
        views.ConsumptionView.as_view(),
        name="salon-consumption",
    ),
    # Payments at the salon, invoices.
    path(f"{S}/payments/methods", views.PaymentMethodsView.as_view(), name="salon-methods"),
    path(f"{S}/payments", views.OnSitePaymentsView.as_view(), name="salon-payments"),
    path(
        f"{S}/payments/<uuid:payment_id>/cancel",
        views.OnSiteCancelView.as_view(),
        name="salon-payment-cancel",
    ),
    path(
        f"{S}/payments/<uuid:payment_id>/receipt",
        views.OnSiteReceiptView.as_view(),
        name="salon-payment-receipt",
    ),
    path(
        f"{S}/appointments/<uuid:appointment_id>/invoice",
        views.AppointmentInvoiceView.as_view(),
        name="salon-appointment-invoice",
    ),
    # Campaigns.
    path(f"{S}/campaigns", views.CampaignsView.as_view(), name="salon-campaigns"),
    path(f"{S}/campaigns/<uuid:campaign_id>", views.CampaignView.as_view(), name="salon-campaign"),
    path(
        f"{S}/campaigns/<uuid:campaign_id>/send",
        views.CampaignSendView.as_view(),
        name="salon-campaign-send",
    ),
    path("unsubscribe/<str:token>", views.UnsubscribeView.as_view(), name="unsubscribe"),
    # Clients.
    path("pros/<slug:slug>/offers", views.PublicOffersView.as_view(), name="salon-offers"),
    path(
        "pros/<slug:slug>/packages/<uuid:package_id>/buy",
        views.BuyPackageView.as_view(),
        name="salon-package-buy",
    ),
    path("pros/<slug:slug>/gift-cards", views.BuyGiftCardView.as_view(), name="salon-gift-buy"),
    path(
        "salon/installments/<uuid:installment_id>/pay",
        views.PayInstallmentView.as_view(),
        name="salon-installment-pay",
    ),
    path("salon/mine", views.MyPackagesView.as_view(), name="salon-mine"),
]
