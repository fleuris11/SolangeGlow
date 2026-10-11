from __future__ import annotations

from django.contrib.gis.geos import Point
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import exceptions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import (
    CookieJWTAuthentication,
    OptionalCookieJWTAuthentication,
)
from apps.accounts.cookies import GUEST_COOKIE
from apps.accounts.models import GuestIdentity
from apps.accounts.throttling import SettingRateThrottle
from apps.core.models import Country
from apps.core.selectors import get_setting

from . import errors, printables, search, selectors, services
from . import serializers as s
from .models import PortfolioItem, ProProfile, Service

# --- Public --------------------------------------------------------------------------------


class PublicProView(APIView):
    """Open to everyone; a signed-in visitor is recognised (her own draft, her name)."""

    permission_classes = [AllowAny]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "search"

    def get_authenticators(self):
        if getattr(self, "swagger_fake_view", False):  # one sign-in scheme in the schema
            return [CookieJWTAuthentication()]
        return [OptionalCookieJWTAuthentication()]


class TradeListView(APIView):
    """Trades offered at sign-up and in search, in the language of the request."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(tags=["catalogue"], responses=s.TradeSerializer(many=True))
    def get(self, request):
        return Response(s.TradeSerializer(selectors.active_trades(), many=True).data)


def _params(data: dict) -> search.SearchParams:
    near = None
    if data.get("lat") is not None and data.get("lng") is not None:
        near = Point(data["lng"], data["lat"], srid=4326)
    return search.SearchParams(
        q=data.get("q", ""),
        trade=data.get("trade", ""),
        city=data.get("city", ""),
        district=data.get("district", ""),
        near=near,
        radius_km=data.get("radius_km"),
        price_max=data.get("price_max"),
        currency=data.get("currency", ""),
        rating_min=data.get("rating_min"),
        open_now=data.get("open_now", False),
        at_home=data.get("at_home", False),
        verified=data.get("verified", False),
        bbox=data.get("bbox"),
        sort=data.get("sort", ""),
    )


class ProSearchView(PublicProView):
    """Pros by words, trade, place, distance, price, rating, opening hours, home visits."""

    @extend_schema(
        operation_id="pros_search",
        tags=["pros"],
        parameters=[s.SearchQuerySerializer],
        responses=s.SearchResultsSerializer,
    )
    def get(self, request):
        query = s.SearchQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        pros = search.search(_params(query.validated_data))
        size = int(get_setting("search.page_size", default=20))
        offset = search.decode_cursor(query.validated_data.get("cursor"))
        page = list(selectors.card_queryset(pros)[offset : offset + size + 1])
        has_more = len(page) > size
        return Response(
            {
                "results": [s.card_payload(pro) for pro in page[:size]],
                "next": search.encode_cursor(offset + size) if has_more else None,
                "count": pros.count() if offset == 0 else -1,
            }
        )


class ProMapView(PublicProView):
    """Points of the pros in the visible part of the map (GeoJSON; grouped by the app)."""

    @extend_schema(
        tags=["pros"], parameters=[s.MapQuerySerializer], responses=s.MapResultsSerializer
    )
    def get(self, request):
        query = s.MapQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        maximum = int(get_setting("search.map_max_points", default=500))
        pros = (
            search.search(_params(query.validated_data))
            .filter(location__isnull=False)
            .prefetch_related("trades")
        )
        rows = list(pros[: maximum + 1])
        features = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [pro.location.x, pro.location.y]},
                "properties": {
                    "slug": pro.slug,
                    "name": pro.display_name,
                    "trade": next((t.icon for t in pro.trades.all()), None),
                    "rating": float(pro.rating_average) if pro.rating_average else None,
                    "verified": pro.is_verified,
                },
            }
            for pro in rows[:maximum]
        ]
        return Response(
            {"type": "FeatureCollection", "features": features, "truncated": len(rows) > maximum}
        )


class PlacesView(PublicProView):
    """Cities and districts with published pros (filters of Explore)."""

    @extend_schema(tags=["pros"], responses=s.CitySerializer(many=True))
    def get(self, request):
        return Response(selectors.places())


class MapConfigView(APIView):
    """Map tiles (style URL and attribution set in the admin) and the starting view."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["pros"],
        parameters=[OpenApiParameter("country", str, required=False)],
        responses=s.MapConfigSerializer,
    )
    def get(self, request):
        code = (request.query_params.get("country") or "").upper()[:2]
        country = Country.objects.filter(code=code).first() if code else None
        center = get_setting(
            "maps.default_center",
            country=country,
            default={"latitude": 6.3654, "longitude": 2.4183, "zoom": 12},
        )
        return Response(
            {
                "style_url": get_setting(
                    "maps.style_url", default="https://tiles.openfreemap.org/styles/liberty"
                ),
                "attribution": get_setting(
                    "maps.attribution", default="© OpenStreetMap, OpenFreeMap"
                ),
                "latitude": float(center["latitude"]),
                "longitude": float(center["longitude"]),
                "zoom": float(center.get("zoom", 12)),
            }
        )


class ShowcaseView(PublicProView):
    """Public page of a pro. Its owner also sees it before publication (preview)."""

    throttle_scope = None
    throttle_classes = []

    @extend_schema(operation_id="pro_showcase", tags=["pros"], responses=s.ShowcaseSerializer)
    def get(self, request, slug):
        pro = selectors.published_pro(slug, viewer=request.user)
        if pro is None:
            raise exceptions.NotFound(errors.ProNotFound.message)
        private = request.user.is_authenticated and pro.user_id == request.user.pk
        return Response(s.showcase_payload(pro, private=private))


PRINTABLES = {
    "card.png": (printables.card_png, "image/png"),
    "poster.pdf": (printables.poster_pdf, "application/pdf"),
    "stickers.pdf": (printables.stickers_pdf, "application/pdf"),
}


class PrintableView(PublicProView):
    """QR code of the short link: card (PNG), A4 poster (PDF), sticker sheet (PDF)."""

    throttle_scope = "printable"

    @extend_schema(
        tags=["pros"], responses={(200, "application/octet-stream"): OpenApiTypes.BINARY}
    )
    def get(self, request, slug, name):
        pro = selectors.published_pro(slug, viewer=request.user)
        if pro is None or name not in PRINTABLES:
            raise exceptions.NotFound(errors.ProNotFound.message)
        render, content_type = PRINTABLES[name]
        response = HttpResponse(render(pro), content_type=content_type)
        filename = f"solangeglow-{slugify(pro.slug)}-{name}"
        download = request.query_params.get("download") == "1"
        response["Content-Disposition"] = (
            f'{"attachment" if download else "inline"}; filename="{filename}"'
        )
        response["Cache-Control"] = "private, max-age=300"
        return response


class ArrivalView(PublicProView):
    """« I am outside »: tells the pro right away that her client is at the door."""

    throttle_scope = "arrival"

    @extend_schema(tags=["pros"], request=None, responses=s.ArrivalSerializer)
    def post(self, request, slug):
        pro = selectors.published_pro(slug)
        if pro is None:
            raise exceptions.NotFound(errors.ProNotFound.message)
        if request.user.is_authenticated:
            services.announce_arrival(pro, user=request.user)
        else:
            guest = GuestIdentity.objects.filter(
                pk=request.COOKIES.get(GUEST_COOKIE) or None, user__isnull=True
            ).first()
            if guest is None:
                raise errors.IdentityRequired()
            services.announce_arrival(pro, guest_name=guest.first_name, guest_key=str(guest.pk))
        return Response({"sent": True})


# --- My showcase ---------------------------------------------------------------------------


class MyProBaseView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "profile"

    def pro(self, request) -> ProProfile:
        return services.get_pro(request.user)

    def payload(self, pro: ProProfile) -> Response:
        fresh = selectors.showcase_queryset().get(pk=pro.pk)
        return Response(s.my_pro_payload(fresh))


class MyProView(MyProBaseView):
    @extend_schema(tags=["my-showcase"], responses=s.MyProSerializer)
    def get(self, request):
        return self.payload(self.pro(request))

    @extend_schema(
        tags=["my-showcase"],
        request=s.BecomeProSerializer,
        responses={201: s.MyProSerializer},
    )
    def post(self, request):
        """« Become a pro »: creates (or resumes) a draft showcase."""
        data = s.BecomeProSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        pro = services.become_pro(
            request.user,
            business_name=values["business_name"],
            kind=values.get("kind", ProProfile.Kind.INDEPENDENT),
            trade_keys=values.get("trades"),
            city=values.get("city", ""),
            district=values.get("district", ""),
        )
        response = self.payload(pro)
        response.status_code = status.HTTP_201_CREATED
        return response

    @extend_schema(tags=["my-showcase"], request=s.ProUpdateSerializer, responses=s.MyProSerializer)
    def patch(self, request):
        data = s.ProUpdateSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        changes = dict(data.validated_data)
        if "trades" in changes:
            changes["trade_keys"] = changes.pop("trades")
        pro = services.update_profile(self.pro(request), actor=request.user, **changes)
        return self.payload(pro)


class SlugCheckView(MyProBaseView):
    @extend_schema(
        tags=["my-showcase"],
        parameters=[OpenApiParameter("slug", str, required=True)],
        responses=s.SlugCheckSerializer,
    )
    def get(self, request):
        pro = self.pro(request)
        wanted = (request.query_params.get("slug") or "").strip().lower()
        try:
            slug = services.check_slug(wanted, pro=pro)
            available = True
        except (errors.SlugInvalid, errors.SlugTaken):
            slug = services.suggest_slug(wanted or pro.business_name, pro=pro)
            available = False
        probe = ProProfile(slug=slug)
        return Response(
            {"slug": slug, "available": available, "short_link": services.short_link(probe)}
        )


class MyProMediaView(MyProBaseView):
    """Photo, cover, voice notes and itinerary video of the showcase."""

    parser_classes = [MultiPartParser, FormParser]
    throttle_scope = "media_upload"

    def _field(self, field: str) -> str:
        if field not in services.MEDIA_FIELDS:
            raise exceptions.NotFound()
        return field

    @extend_schema(
        tags=["my-showcase"],
        request={"multipart/form-data": s.FileUploadSerializer},
        responses={202: s.MyProSerializer},
    )
    def post(self, request, field):
        upload = s.FileUploadSerializer(data=request.data)
        upload.is_valid(raise_exception=True)
        pro = services.set_media(
            self.pro(request), self._field(field), upload.validated_data["file"]
        )
        response = self.payload(pro)
        response.status_code = status.HTTP_202_ACCEPTED
        return response

    @extend_schema(tags=["my-showcase"], request=None, responses={200: s.MyProSerializer})
    def delete(self, request, field):
        pro = services.clear_media(self.pro(request), self._field(field))
        return self.payload(pro)


class MyLocationView(MyProBaseView):
    parser_classes = [JSONParser]

    @extend_schema(tags=["my-showcase"], request=s.LocationSerializer, responses=s.MyProSerializer)
    def put(self, request):
        data = s.LocationSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        pro = services.set_location(
            self.pro(request),
            latitude=values["latitude"],
            longitude=values["longitude"],
            source=values["source"],
            actor=request.user,
        )
        return self.payload(pro)


class MyTravelView(MyProBaseView):
    parser_classes = [JSONParser]

    @extend_schema(
        tags=["my-showcase"], request=s.TravelUpdateSerializer, responses=s.MyProSerializer
    )
    def put(self, request):
        data = s.TravelUpdateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        pro = services.set_travel(
            self.pro(request),
            travels=values["travels_to_clients"],
            radius_km=values.get("radius_km"),
            area=values.get("area"),
            fee_minor=values.get("fee_minor"),
            actor=request.user,
        )
        return self.payload(pro)


class MyPublicationView(MyProBaseView):
    @extend_schema(tags=["my-showcase"], request=None, responses=s.MyProSerializer)
    def post(self, request):
        """Publish: the showcase becomes visible in searches and at its short link."""
        return self.payload(services.publish(self.pro(request), actor=request.user))

    @extend_schema(tags=["my-showcase"], request=None, responses={200: s.MyProSerializer})
    def delete(self, request):
        """Back to draft: hidden from everyone but her."""
        return self.payload(services.unpublish(self.pro(request), actor=request.user))


class MyServicesView(MyProBaseView):
    parser_classes = [JSONParser]

    @extend_schema(tags=["my-showcase"], responses=s.ServiceSerializer(many=True))
    def get(self, request):
        services_ = selectors.visible_services().filter(pro=self.pro(request))
        hidden = Service.objects.filter(
            pro__user=request.user, is_active=False, archived_at__isnull=True
        ).prefetch_related("steps", "options", "photos__media")
        rows = [*services_, *hidden]
        return Response(s.ServiceSerializer(rows, many=True, context={"owner": True}).data)

    @extend_schema(
        tags=["my-showcase"],
        request=s.ServiceWriteSerializer,
        responses={201: s.ServiceSerializer},
    )
    def post(self, request):
        data = s.ServiceWriteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        service = services.save_service(self.pro(request), dict(data.validated_data))
        return Response(
            s.ServiceSerializer(service, context={"owner": True}).data,
            status=status.HTTP_201_CREATED,
        )


class MyServiceView(MyProBaseView):
    parser_classes = [JSONParser]

    def service(self, request, service_id) -> Service:
        return get_object_or_404(
            Service, pk=service_id, pro__user=request.user, archived_at__isnull=True
        )

    @extend_schema(
        tags=["my-showcase"], request=s.ServiceWriteSerializer, responses=s.ServiceSerializer
    )
    def patch(self, request, service_id):
        service = self.service(request, service_id)
        data = s.ServiceWriteSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        service = services.save_service(service.pro, dict(data.validated_data), service=service)
        return Response(s.ServiceSerializer(service, context={"owner": True}).data)

    @extend_schema(tags=["my-showcase"], request=None, responses={204: None})
    def delete(self, request, service_id):
        services.archive_service(self.service(request, service_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyServicePhotosView(MyProBaseView):
    parser_classes = [MultiPartParser, FormParser]
    throttle_scope = "media_upload"

    @extend_schema(
        tags=["my-showcase"],
        request={"multipart/form-data": s.FileUploadSerializer},
        responses={202: s.ServiceSerializer},
    )
    def post(self, request, service_id):
        service = get_object_or_404(
            Service, pk=service_id, pro__user=request.user, archived_at__isnull=True
        )
        upload = s.FileUploadSerializer(data=request.data)
        upload.is_valid(raise_exception=True)
        services.add_service_photo(service, upload.validated_data["file"])
        return Response(
            s.ServiceSerializer(service, context={"owner": True}).data,
            status=status.HTTP_202_ACCEPTED,
        )


class MyServicePhotoView(MyProBaseView):
    @extend_schema(tags=["my-showcase"], request=None, responses={204: None})
    def delete(self, request, service_id, photo_id):
        service = get_object_or_404(Service, pk=service_id, pro__user=request.user)
        photo = get_object_or_404(service.photos, pk=photo_id)
        services.remove_service_photo(photo)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyCategoriesView(MyProBaseView):
    parser_classes = [JSONParser]

    @extend_schema(tags=["my-showcase"], responses=s.CategorySerializer(many=True))
    def get(self, request):
        pro = self.pro(request)
        return Response(s.CategorySerializer(pro.categories.all(), many=True).data)

    @extend_schema(
        tags=["my-showcase"], request=s.CategorySerializer, responses={201: s.CategorySerializer}
    )
    def post(self, request):
        data = s.CategorySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        category = services.save_category(
            self.pro(request),
            name=data.validated_data["name"],
            position=data.validated_data.get("position", 0),
        )
        return Response(s.CategorySerializer(category).data, status=status.HTTP_201_CREATED)


class MyCategoryView(MyProBaseView):
    parser_classes = [JSONParser]

    @extend_schema(
        tags=["my-showcase"], request=s.CategorySerializer, responses=s.CategorySerializer
    )
    def patch(self, request, category_id):
        pro = self.pro(request)
        category = get_object_or_404(pro.categories, pk=category_id)
        data = s.CategorySerializer(category, data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        category = services.save_category(
            pro,
            name=data.validated_data.get("name", category.name),
            position=data.validated_data.get("position", category.position),
            category=category,
        )
        return Response(s.CategorySerializer(category).data)

    @extend_schema(tags=["my-showcase"], request=None, responses={204: None})
    def delete(self, request, category_id):
        pro = self.pro(request)
        services.delete_category(get_object_or_404(pro.categories, pk=category_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyHoursView(MyProBaseView):
    parser_classes = [JSONParser]

    def hours(self, pro):
        return Response(
            {
                "periods": s.PeriodSerializer(pro.opening_periods.all(), many=True).data,
                "closures": s.ClosureSerializer(pro.closures.all(), many=True).data,
            }
        )

    @extend_schema(tags=["my-showcase"], responses=s.HoursSerializer)
    def get(self, request):
        return self.hours(self.pro(request))

    @extend_schema(tags=["my-showcase"], request=s.HoursSerializer, responses=s.HoursSerializer)
    def put(self, request):
        """Replaces the whole week (several periods on a day = breaks between them)."""
        data = s.HoursSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        pro = self.pro(request)
        services.set_opening_hours(pro, data.validated_data["periods"])
        return self.hours(pro)


class MyClosuresView(MyProBaseView):
    parser_classes = [JSONParser]

    @extend_schema(
        tags=["my-showcase"], request=s.ClosureSerializer, responses={201: s.ClosureSerializer}
    )
    def post(self, request):
        data = s.ClosureSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        closure = services.add_closure(
            self.pro(request),
            starts_on=data.validated_data["starts_on"],
            ends_on=data.validated_data["ends_on"],
            reason=data.validated_data.get("reason", ""),
        )
        return Response(s.ClosureSerializer(closure).data, status=status.HTTP_201_CREATED)


class MyClosureView(MyProBaseView):
    @extend_schema(tags=["my-showcase"], request=None, responses={204: None})
    def delete(self, request, closure_id):
        pro = self.pro(request)
        get_object_or_404(pro.closures, pk=closure_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyPortfolioView(MyProBaseView):
    parser_classes = [MultiPartParser, FormParser]

    def get_throttles(self):
        self.throttle_scope = "media_upload" if self.request.method == "POST" else "profile"
        return super().get_throttles()

    @extend_schema(tags=["my-showcase"], responses=s.PortfolioItemSerializer(many=True))
    def get(self, request):
        items = PortfolioItem.objects.filter(pro__user=request.user).select_related(
            "media", "before_media", "service"
        )
        return Response(s.PortfolioItemSerializer(items, many=True).data)

    @extend_schema(
        tags=["my-showcase"],
        request={"multipart/form-data": s.PortfolioUploadSerializer},
        responses={202: s.PortfolioItemSerializer},
    )
    def post(self, request):
        data = s.PortfolioUploadSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        pro = self.pro(request)
        values = data.validated_data
        service = (
            pro.services.filter(pk=values["service_id"]).first()
            if values.get("service_id")
            else None
        )
        with transaction.atomic():
            item = services.add_portfolio_item(
                pro,
                uploaded=values["file"],
                before=values.get("before"),
                caption=values.get("caption", ""),
                service=service,
            )
        return Response(s.PortfolioItemSerializer(item).data, status=status.HTTP_202_ACCEPTED)


class MyPortfolioItemView(MyProBaseView):
    parser_classes = [JSONParser]

    def item(self, request, item_id) -> PortfolioItem:
        return get_object_or_404(PortfolioItem, pk=item_id, pro__user=request.user)

    @extend_schema(
        tags=["my-showcase"],
        request=s.PortfolioUpdateSerializer,
        responses=s.PortfolioItemSerializer,
    )
    def patch(self, request, item_id):
        data = s.PortfolioUpdateSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        item = services.update_portfolio_item(self.item(request, item_id), **data.validated_data)
        return Response(s.PortfolioItemSerializer(item).data)

    @extend_schema(tags=["my-showcase"], request=None, responses={204: None})
    def delete(self, request, item_id):
        services.delete_portfolio_item(self.item(request, item_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyVerificationView(MyProBaseView):
    parser_classes = [MultiPartParser, FormParser]

    def get_throttles(self):
        self.throttle_scope = "verification" if self.request.method == "POST" else "profile"
        return super().get_throttles()

    @extend_schema(tags=["my-showcase"], responses=s.VerificationStateSerializer)
    def get(self, request):
        return Response(s.verification_payload(self.pro(request)))

    @extend_schema(
        tags=["my-showcase"],
        request={"multipart/form-data": s.VerificationUploadSerializer},
        responses={202: s.VerificationStateSerializer},
    )
    def post(self, request):
        """Identity document + selfie, encrypted and sent to the verification team."""
        data = s.VerificationUploadSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        pro = self.pro(request)
        services.submit_verification(
            pro,
            document=data.validated_data["document"],
            selfie=data.validated_data["selfie"],
            document_type=data.validated_data["document_type"],
        )
        pro.refresh_from_db()
        return Response(s.verification_payload(pro), status=status.HTTP_202_ACCEPTED)
