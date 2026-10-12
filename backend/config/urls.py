from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.api.views import CountryListView, HealthView
from apps.core.media.api import MediaDetailView, MediaUploadView

api_v1 = [
    path("health", HealthView.as_view(), name="health"),
    path("countries", CountryListView.as_view(), name="countries"),
    path("", include("apps.social.urls")),
    path("", include("apps.moderation.urls")),
    path("", include("apps.messaging.urls")),
    path("", include("apps.pros.urls")),
    path("", include("apps.accounts.urls")),
    path("", include("apps.notifications.urls")),
    path("media", MediaUploadView.as_view(), name="media-upload"),
    path("media/<uuid:asset_id>", MediaDetailView.as_view(), name="media-detail"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("api/v1/", include((api_v1, "api"), namespace="v1")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="api-docs"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
