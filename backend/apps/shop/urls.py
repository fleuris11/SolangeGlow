from django.urls import path

from . import views

ORDER = "shop/orders/<uuid:order_id>"
MP = "me/shop/products/<uuid:product_id>"

urlpatterns = [
    # Public: shops and products.
    path("shop/categories", views.CategoriesView.as_view(), name="shop-categories"),
    path("pros/<slug:slug>/shop", views.ShopPageView.as_view(), name="shop-page"),
    path(
        "pros/<slug:slug>/shop/<slug:product_slug>",
        views.ProductBySlugView.as_view(),
        name="shop-product-by-slug",
    ),
    path("shop/products/<uuid:product_id>", views.ProductView.as_view(), name="shop-product"),
    path(
        "shop/products/<uuid:product_id>/reviews",
        views.ProductReviewsView.as_view(),
        name="shop-product-reviews",
    ),
    # Client: cart, checkout, orders, wishlist, alerts.
    path("shop/cart", views.CartView.as_view(), name="shop-cart"),
    path("shop/cart/items", views.CartItemsView.as_view(), name="shop-cart-items"),
    path("shop/cart/items/<uuid:item_id>", views.CartItemView.as_view(), name="shop-cart-item"),
    path("shop/checkout/quote", views.QuoteView.as_view(), name="shop-quote"),
    path("shop/checkout", views.CheckoutView.as_view(), name="shop-checkout"),
    path("shop/orders", views.OrderListView.as_view(), name="shop-orders"),
    path(ORDER, views.OrderView.as_view(), name="shop-order"),
    path(f"{ORDER}/prepare", views.OrderPrepareView.as_view(), name="shop-order-prepare"),
    path(f"{ORDER}/ship", views.OrderShipView.as_view(), name="shop-order-ship"),
    path(f"{ORDER}/ready", views.OrderReadyView.as_view(), name="shop-order-ready"),
    path(f"{ORDER}/cancel", views.OrderCancelView.as_view(), name="shop-order-cancel"),
    path(f"{ORDER}/pay", views.OrderPayView.as_view(), name="shop-order-pay"),
    path("shop/wishlist", views.WishlistView.as_view(), name="shop-wishlist"),
    path(
        "shop/wishlist/<uuid:product_id>",
        views.WishlistItemView.as_view(),
        name="shop-wishlist-item",
    ),
    path("shop/alerts/<uuid:variant_id>", views.StockAlertView.as_view(), name="shop-alert"),
    # The pro: « My shop ».
    path("me/shop", views.MyShopView.as_view(), name="my-shop"),
    path("me/shop/zones", views.ZonesView.as_view(), name="my-shop-zones"),
    path("me/shop/zones/<uuid:zone_id>", views.ZoneView.as_view(), name="my-shop-zone"),
    path("me/shop/products", views.MyProductsView.as_view(), name="my-products"),
    path(MP, views.MyProductView.as_view(), name="my-product"),
    path(f"{MP}/publish", views.PublishProductView.as_view(), name="my-product-publish"),
    path(f"{MP}/pause", views.PauseProductView.as_view(), name="my-product-pause"),
    path(
        "me/shop/variants/<uuid:variant_id>",
        views.VariantStockView.as_view(),
        name="my-variant-stock",
    ),
    path("me/shop/promotions", views.PromotionsView.as_view(), name="my-promotions"),
    path("me/shop/promos", views.PromosView.as_view(), name="my-promos"),
    path("me/shop/promos/<uuid:promo_id>", views.PromoView.as_view(), name="my-promo"),
    path("me/shop/flash-sales", views.FlashSalesView.as_view(), name="my-flash-sales"),
    path("me/shop/flash-sales/<uuid:sale_id>", views.FlashSaleView.as_view(), name="my-flash-sale"),
    path("me/shop/bundles", views.BundlesView.as_view(), name="my-bundles"),
    path("me/shop/bundles/<uuid:bundle_id>", views.BundleView.as_view(), name="my-bundle"),
    path("me/shop/stats", views.StatsView.as_view(), name="my-shop-stats"),
    path("me/shop/lives", views.MySaleLivesView.as_view(), name="my-sale-lives"),
    path(
        "me/shop/lives/<uuid:live_id>/cancel",
        views.MySaleLiveCancelView.as_view(),
        name="my-sale-live-cancel",
    ),
    path(
        "me/shop/lives/<uuid:live_id>/pins/<uuid:product_id>",
        views.MySaleLivePinView.as_view(),
        name="my-sale-live-pin",
    ),
]
