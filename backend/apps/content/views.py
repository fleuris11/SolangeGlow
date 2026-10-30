from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from apps.accounts.views_base import OptionalAuthView
from apps.core.media.api import MediaSerializer
from apps.core.media.services import asset_payload
from apps.core.selectors import get_setting

from . import errors
from .models import Banner, FaqItem, Page, Ticket
from .services import help as help_services

TAGS = ["content"]


class ContentView(OptionalAuthView):
    throttle_scope = "content"


def _viewer(request):
    return request.user if request.user.is_authenticated else None


def _language(request) -> str:
    return getattr(request, "LANGUAGE_CODE", "fr") or "fr"


# --- Pages ---------------------------------------------------------------------------------------


class PageSummarySerializer(serializers.Serializer):
    slug = serializers.CharField()
    kind = serializers.ChoiceField(choices=Page.Kind.choices)
    title = serializers.CharField()
    summary = serializers.CharField(allow_blank=True)


class PageSerializer(PageSummarySerializer):
    body = serializers.CharField()
    updated_at = serializers.DateTimeField()
    version = serializers.IntegerField()


class PagesView(ContentView):
    @extend_schema(tags=TAGS, responses=PageSummarySerializer(many=True))
    def get(self, request):
        rows = Page.objects.filter(is_published=True)
        return Response(PageSummarySerializer(rows, many=True).data)


class PageView(ContentView):
    @extend_schema(tags=TAGS, responses=PageSerializer)
    def get(self, request, slug):
        page = Page.objects.filter(slug=slug, is_published=True).first()
        if page is None:
            raise errors.PageNotFound()
        return Response(PageSerializer(page).data)


# --- Home banners --------------------------------------------------------------------------------


class BannerSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    text = serializers.CharField(allow_blank=True)
    cta = serializers.CharField(allow_blank=True)
    link = serializers.CharField(allow_blank=True)
    image = MediaSerializer(allow_null=True)


class BannerQuerySerializer(serializers.Serializer):
    country = serializers.CharField(required=False, default="", allow_blank=True, max_length=2)


class BannersView(ContentView):
    @extend_schema(
        tags=TAGS, parameters=[BannerQuerySerializer], responses=BannerSerializer(many=True)
    )
    def get(self, request):
        query = BannerQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        viewer = _viewer(request)
        country = (
            viewer.country.code if viewer and viewer.country_id else query.validated_data["country"]
        ).upper()
        now = timezone.now()
        rows = Banner.objects.filter(is_active=True).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(ends_at__isnull=True) | Q(ends_at__gt=now),
        )
        found = [b for b in rows if not b.countries or not country or country in b.countries]
        most = int(get_setting("content.banners_max", default=1))
        payload = [
            {
                "id": b.pk,
                "title": b.title,
                "text": b.text,
                "cta": b.cta,
                "link": b.link,
                "image": asset_payload(b.image) if b.image_id and b.image.is_ready else None,
            }
            for b in found[:most]
        ]
        return Response(BannerSerializer(payload, many=True).data)


# --- Help center ---------------------------------------------------------------------------------


class FaqItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    topic = serializers.ChoiceField(choices=FaqItem.Topic.choices)
    question = serializers.CharField()
    answer = serializers.CharField()


class FaqTopicSerializer(serializers.Serializer):
    key = serializers.ChoiceField(choices=FaqItem.Topic.choices)
    label = serializers.CharField()
    items = FaqItemSerializer(many=True)


class FaqView(ContentView):
    @extend_schema(tags=TAGS, responses=FaqTopicSerializer(many=True))
    def get(self, request):
        items = list(FaqItem.objects.filter(is_published=True))
        topics = []
        for key, label in FaqItem.Topic.choices:
            mine = [i for i in items if i.topic == key]
            if mine:
                topics.append({"key": key, "label": str(label), "items": mine})
        return Response(FaqTopicSerializer(topics, many=True).data)


class SuggestInputSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=1000)


class SuggestSerializer(serializers.Serializer):
    answer = serializers.CharField(allow_null=True)
    faq = FaqItemSerializer(many=True)


class SuggestView(ContentView):
    """The answers that may help before sending a question to the team."""

    @extend_schema(tags=TAGS, request=SuggestInputSerializer, responses=SuggestSerializer)
    def post(self, request):
        data = SuggestInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        found = help_services.suggestions(data.validated_data["question"], _language(request))
        return Response(SuggestSerializer(found).data)


class TicketInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    topic = serializers.ChoiceField(
        choices=FaqItem.Topic.choices, required=False, allow_blank=True, default=""
    )
    message = serializers.CharField(max_length=3000)


class TicketSerializer(serializers.Serializer):
    reference = serializers.CharField()
    status = serializers.ChoiceField(choices=Ticket.Status.choices)


class TicketsView(ContentView):
    throttle_scope = "help_ticket"

    @extend_schema(tags=TAGS, request=TicketInputSerializer, responses={201: TicketSerializer})
    def post(self, request):
        data = TicketInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        ticket = help_services.create_ticket(
            user=_viewer(request), language=_language(request), **data.validated_data
        )
        return Response(TicketSerializer(ticket).data, status=status.HTTP_201_CREATED)
