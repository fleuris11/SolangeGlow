from django.conf import settings
from django.shortcuts import render
from django.utils import translation
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.cookies import clear_auth_cookies
from apps.accounts.throttling import SettingRateThrottle
from apps.accounts.views_base import OptionalAuthView

from .models import Prospect
from .services import impersonation, prospects, translations

TAGS = ["backoffice"]


class OverridesQuerySerializer(serializers.Serializer):
    lang = serializers.ChoiceField(choices=settings.LANGUAGES)


class OverridesSerializer(serializers.Serializer):
    version = serializers.IntegerField()
    messages = serializers.DictField(child=serializers.CharField())


class OverridesView(OptionalAuthView):
    """The texts of the app corrected in the admin (the app keeps them one minute)."""

    throttle_scope = "content"

    @extend_schema(tags=TAGS, parameters=[OverridesQuerySerializer], responses=OverridesSerializer)
    def get(self, request):
        query = OverridesQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        language = query.validated_data["lang"]
        payload = {
            "version": translations.version(),
            "messages": translations.web_overrides(language),
        }
        return Response(OverridesSerializer(payload).data)


class StopImpersonationView(APIView):
    """Ends « sign in as »: the session of the member is closed on this browser."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=TAGS, request=None, responses={204: None})
    def post(self, request):
        claim = request.auth.get(impersonation.CLAIM) if request.auth else None
        if claim:
            impersonation.stop(claim, user=request.user)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_auth_cookies(response)
        response.delete_cookie(
            impersonation.BANNER_COOKIE, path="/", domain=settings.AUTH_COOKIES["DOMAIN"]
        )
        return response


class ClaimSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=20)


class ProspectClaimView(APIView):
    """A pro signed up with the link of her invitation (prospecting)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "content"

    @extend_schema(tags=TAGS, request=ClaimSerializer, responses={204: None})
    def post(self, request):
        data = ClaimSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        prospects.claim(request.user, data.validated_data["code"])
        return Response(status=status.HTTP_204_NO_CONTENT)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def prospect_stop(request, code: str):
    """« Not interested »: the link at the bottom of every e-mail sent to a prospect.

    Opening the link only asks to confirm (mail scanners open links); the button stops the
    e-mails. No account, no cookie: the code of the link is the proof."""
    prospect = Prospect.objects.filter(invite_code=code).first()
    language = prospect.language if prospect else translation.get_language() or "fr"
    done = False
    if request.method == "POST" and prospect is not None:
        done = prospects.decline(code)
    with translation.override(language):
        response = render(
            request,
            "backoffice/prospect_stop.html",
            {
                "found": prospect is not None,
                "done": done,
                "language": language,
                "has_page": bool(prospect and prospect.pro_id and prospect.pro.prepared_by_team),
            },
            status=200 if prospect is not None else 404,
        )
    response["X-Robots-Tag"] = "noindex"
    return response
