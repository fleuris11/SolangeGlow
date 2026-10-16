from django.urls import path

from . import views

ORDER = "selection/orders/<uuid:order_id>"
REQUEST = "selection/requests/<uuid:request_id>"

urlpatterns = [
    path("selection/products", views.ProductListView.as_view(), name="selection-products"),
    path("selection/products/<slug:slug>", views.ProductView.as_view(), name="selection-product"),
    path(
        "selection/pickup-points", views.PickupPointsView.as_view(), name="selection-pickup-points"
    ),
    path("selection/orders", views.OrdersView.as_view(), name="selection-orders"),
    path(ORDER, views.OrderView.as_view(), name="selection-order"),
    path(f"{ORDER}/cancel", views.OrderCancelView.as_view(), name="selection-order-cancel"),
    path(f"{ORDER}/pay", views.OrderPayView.as_view(), name="selection-order-pay"),
    path("selection/requests", views.RequestsView.as_view(), name="selection-requests"),
    path(f"{REQUEST}/order", views.RequestOrderView.as_view(), name="selection-request-order"),
    path(
        f"{REQUEST}/decline", views.RequestDeclineView.as_view(), name="selection-request-decline"
    ),
]
