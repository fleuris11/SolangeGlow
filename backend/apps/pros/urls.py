from django.urls import path

from . import views

urlpatterns = [
    path("trades", views.TradeListView.as_view(), name="trades"),
    path("pros", views.ProSearchView.as_view(), name="pros-search"),
    path("pros/map", views.ProMapView.as_view(), name="pros-map"),
    path("pros/places", views.PlacesView.as_view(), name="pros-places"),
    path("config/map", views.MapConfigView.as_view(), name="map-config"),
    path("pros/<slug:slug>", views.ShowcaseView.as_view(), name="pro-showcase"),
    path("pros/<slug:slug>/arrival", views.ArrivalView.as_view(), name="pro-arrival"),
    path(
        "pros/<slug:slug>/print/<str:name>",
        views.PrintableView.as_view(),
        name="pro-printable",
    ),
    path("me/pro", views.MyProView.as_view(), name="my-pro"),
    path("me/pro/slug", views.SlugCheckView.as_view(), name="my-pro-slug"),
    path("me/pro/media/<str:field>", views.MyProMediaView.as_view(), name="my-pro-media"),
    path("me/pro/location", views.MyLocationView.as_view(), name="my-pro-location"),
    path("me/pro/travel", views.MyTravelView.as_view(), name="my-pro-travel"),
    path("me/pro/publication", views.MyPublicationView.as_view(), name="my-pro-publication"),
    path("me/pro/services", views.MyServicesView.as_view(), name="my-pro-services"),
    path("me/pro/services/<uuid:service_id>", views.MyServiceView.as_view(), name="my-pro-service"),
    path(
        "me/pro/services/<uuid:service_id>/photos",
        views.MyServicePhotosView.as_view(),
        name="my-pro-service-photos",
    ),
    path(
        "me/pro/services/<uuid:service_id>/photos/<uuid:photo_id>",
        views.MyServicePhotoView.as_view(),
        name="my-pro-service-photo",
    ),
    path("me/pro/categories", views.MyCategoriesView.as_view(), name="my-pro-categories"),
    path(
        "me/pro/categories/<uuid:category_id>",
        views.MyCategoryView.as_view(),
        name="my-pro-category",
    ),
    path("me/pro/hours", views.MyHoursView.as_view(), name="my-pro-hours"),
    path("me/pro/closures", views.MyClosuresView.as_view(), name="my-pro-closures"),
    path("me/pro/closures/<uuid:closure_id>", views.MyClosureView.as_view(), name="my-pro-closure"),
    path("me/pro/portfolio", views.MyPortfolioView.as_view(), name="my-pro-portfolio"),
    path(
        "me/pro/portfolio/<uuid:item_id>",
        views.MyPortfolioItemView.as_view(),
        name="my-pro-portfolio-item",
    ),
    path("me/pro/verification", views.MyVerificationView.as_view(), name="my-pro-verification"),
]
