import contextlib

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import exceptions, serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from . import services
from .authentication import token_is_revoked
from .cookies import (
    GUEST_COOKIE,
    clear_auth_cookies,
    clear_guest_cookie,
    set_auth_cookies,
    set_guest_cookie,
)
from .models import GuestIdentity, User
from .otp.console import DEV_CODE_CACHE_PREFIX
from .serializers import (
    CodeRequestResultSerializer,
    CodeRequestSerializer,
    CodeVerifySerializer,
    ContactChangeConfirmSerializer,
    ContactChangeRequestSerializer,
    DeleteAccountSerializer,
    DeletionScheduledSerializer,
    GuestSerializer,
    MeSerializer,
    OnboardingSerializer,
    PasswordLoginSerializer,
    PasswordSetSerializer,
    PhotoSerializer,
    SignInSerializer,
)
from .throttling import SettingRateThrottle

OK = inline_serializer("Ok", {"status": serializers.CharField()})


def client_ip(request) -> str | None:
    # Behind the production proxy, REMOTE_ADDR is set from X-Forwarded-For by the proxy.
    return request.META.get("REMOTE_ADDR")


def user_agent(request) -> str:
    return request.META.get("HTTP_USER_AGENT", "")


def require_client_header(request) -> None:
    """Cookie-only endpoints (refresh, logout) are protected against cross-site requests."""
    if not request.headers.get(settings.AUTH_CLIENT_HEADER):
        raise exceptions.PermissionDenied(_("Request refused. Reload the page and try again."))


class PublicView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [SettingRateThrottle]

    def get_authenticate_header(self, request):
        # Refused tokens answer 401 (sign in again), not 403 (forbidden).
        return 'Bearer realm="api"'


def signed_in_response(request, result: services.SignInResult) -> Response:
    data = SignInSerializer(
        {
            "created": result.created,
            "deletion_cancelled": result.deletion_cancelled,
            "user": result.user,
        },
        context={"request": request},
    ).data
    code = status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
    response = Response(data, status=code)
    set_auth_cookies(response, RefreshToken.for_user(result.user))
    clear_guest_cookie(response)
    return response


class CodeRequestView(PublicView):
    throttle_scope = "otp_request"

    @extend_schema(
        tags=["auth"],
        request=CodeRequestSerializer,
        responses={202: CodeRequestResultSerializer},
        summary="Send a 6-digit code by WhatsApp, SMS or e-mail (sign-up and sign-in).",
    )
    def post(self, request):
        serializer = CodeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = services.request_code(
            phone=serializer.validated_data.get("phone"),
            email=serializer.validated_data.get("email"),
            ip=client_ip(request),
            locale=serializer.validated_data.get("locale") or request.LANGUAGE_CODE,
        )
        return Response(CodeRequestResultSerializer(result).data, status=status.HTTP_202_ACCEPTED)


class CodeVerifyView(PublicView):
    throttle_scope = "auth"

    @extend_schema(
        tags=["auth"],
        request=CodeVerifySerializer,
        responses={200: SignInSerializer, 201: SignInSerializer},
    )
    def post(self, request):
        serializer = CodeVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = services.verify_code(
            challenge_id=str(serializer.validated_data["challenge_id"]),
            code=serializer.validated_data["code"],
            ip=client_ip(request),
            user_agent=user_agent(request),
            locale=serializer.validated_data.get("locale") or request.LANGUAGE_CODE,
            guest_id=request.COOKIES.get(GUEST_COOKIE),
        )
        return signed_in_response(request, result)


class PasswordLoginView(PublicView):
    throttle_scope = "auth"

    @extend_schema(
        tags=["auth"], request=PasswordLoginSerializer, responses={200: SignInSerializer}
    )
    def post(self, request):
        serializer = PasswordLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = services.login_with_password(
            identifier=serializer.validated_data["identifier"],
            password=serializer.validated_data["password"],
            ip=client_ip(request),
            user_agent=user_agent(request),
        )
        return signed_in_response(request, result)


class RefreshView(PublicView):
    throttle_scope = "auth"

    @extend_schema(tags=["auth"], request=None, responses={200: OK})
    def post(self, request):
        """Rotate the tokens from the refresh cookie (the old refresh token is blacklisted)."""
        require_client_header(request)
        raw = request.COOKIES.get(settings.AUTH_COOKIES["REFRESH_NAME"])
        if not raw:
            raise exceptions.NotAuthenticated()
        try:
            token = RefreshToken(raw)
            user = User.objects.get(pk=token["user_id"])
        except (TokenError, User.DoesNotExist, KeyError) as exc:
            raise exceptions.AuthenticationFailed() from exc
        if not user.is_active or token_is_revoked(user, token.get("iat")):
            raise exceptions.AuthenticationFailed()

        serializer = TokenRefreshSerializer(data={"refresh": raw})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise exceptions.AuthenticationFailed() from exc
        response = Response({"status": "ok"})
        set_auth_cookies(response, RefreshToken(serializer.validated_data["refresh"]))
        return response


class LogoutView(PublicView):
    throttle_scope = "auth"

    @extend_schema(tags=["auth"], request=None, responses={200: OK})
    def post(self, request):
        require_client_header(request)
        raw = request.COOKIES.get(settings.AUTH_COOKIES["REFRESH_NAME"])
        if raw:
            with contextlib.suppress(TokenError):
                RefreshToken(raw).blacklist()
        response = Response({"status": "ok"})
        clear_auth_cookies(response)
        return response


class LogoutAllView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["auth"], request=None, responses={200: OK})
    def post(self, request):
        services.revoke_all_tokens(request.user)
        response = Response({"status": "ok"})
        clear_auth_cookies(response)
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "profile"

    @extend_schema(tags=["me"], responses=MeSerializer)
    def get(self, request):
        return Response(MeSerializer(request.user, context={"request": request}).data)

    @extend_schema(tags=["me"], request=MeSerializer, responses=MeSerializer)
    def patch(self, request):
        serializer = MeSerializer(
            request.user, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        tags=["me"], request=DeleteAccountSerializer, responses={202: DeletionScheduledSerializer}
    )
    def delete(self, request):
        """Asks for deletion: erased after the grace period unless she signs in again."""
        serializer = DeleteAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        erase_after = services.request_deletion(request.user)
        response = Response(
            DeletionScheduledSerializer({"erase_after": erase_after}).data,
            status=status.HTTP_202_ACCEPTED,
        )
        clear_auth_cookies(response)
        return response


class PhotoView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "media_upload"

    @extend_schema(tags=["me"], request=PhotoSerializer, responses={202: MeSerializer})
    def post(self, request):
        """New profile photo: processed in the background (status "processing" then "ready")."""
        serializer = PhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.set_photo(request.user, serializer.validated_data["photo"])
        data = MeSerializer(user, context={"request": request}).data
        return Response(data, status=status.HTTP_202_ACCEPTED)

    @extend_schema(tags=["me"], request=None, responses=MeSerializer)
    def delete(self, request):
        user = services.remove_photo(request.user)
        return Response(MeSerializer(user, context={"request": request}).data)


class ContactChangeRequestView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "otp_request"

    @extend_schema(
        tags=["me"],
        request=ContactChangeRequestSerializer,
        responses={202: CodeRequestResultSerializer},
        summary="Send a code to a new number or e-mail before changing it.",
    )
    def post(self, request):
        serializer = ContactChangeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = services.request_contact_change(
            request.user,
            phone=serializer.validated_data.get("phone"),
            email=serializer.validated_data.get("email"),
            ip=client_ip(request),
            locale=serializer.validated_data.get("locale") or request.LANGUAGE_CODE,
        )
        return Response(CodeRequestResultSerializer(result).data, status=status.HTTP_202_ACCEPTED)


class ContactChangeConfirmView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "auth"

    @extend_schema(tags=["me"], request=ContactChangeConfirmSerializer, responses=MeSerializer)
    def post(self, request):
        serializer = ContactChangeConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.confirm_contact_change(
            request.user,
            challenge_id=str(serializer.validated_data["challenge_id"]),
            code=serializer.validated_data["code"],
        )
        return Response(MeSerializer(user, context={"request": request}).data)


class PasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["me"], request=PasswordSetSerializer, responses={200: OK})
    def post(self, request):
        serializer = PasswordSetSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        services.set_password(request.user, serializer.validated_data["password"])
        return Response({"status": "ok"})


class OnboardingView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["me"], request=OnboardingSerializer, responses=MeSerializer)
    def post(self, request):
        serializer = OnboardingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = services.complete_onboarding(
            request.user,
            mode=data["mode"],
            birth_date=data["birth_date"],
            trade_keys=data.get("trades"),
            language=data.get("language"),
            city=data.get("city", ""),
        )
        return Response(MeSerializer(user, context={"request": request}).data)


class GuestView(PublicView):
    throttle_scope = "guest"

    @extend_schema(tags=["guest"], responses=GuestSerializer)
    def get(self, request):
        guest = GuestIdentity.objects.filter(
            pk=request.COOKIES.get(GUEST_COOKIE) or None, user__isnull=True
        ).first()
        if guest is None:
            raise exceptions.NotFound()
        return Response(GuestSerializer(guest).data)

    @extend_schema(tags=["guest"], request=GuestSerializer, responses={201: GuestSerializer})
    def post(self, request):
        serializer = GuestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        guest = services.create_guest(
            first_name=serializer.validated_data["first_name"],
            phone=serializer.validated_data["phone"],
        )
        response = Response(GuestSerializer(guest).data, status=status.HTTP_201_CREATED)
        set_guest_cookie(response, str(guest.pk))
        return response


class DevLastCodeView(PublicView):
    """Development only (never routed in production): last code sent to a destination."""

    throttle_classes = []

    @extend_schema(
        tags=["dev"],
        parameters=[OpenApiParameter("destination", str, required=True)],
        responses=inline_serializer("DevCode", {"code": serializers.CharField()}),
    )
    def get(self, request):
        if not settings.ACCOUNTS_DEV_OTP_ENDPOINT:
            raise exceptions.NotFound()
        destination = request.query_params.get("destination", "").strip().lower()
        code = cache.get(DEV_CODE_CACHE_PREFIX + destination)
        if code is None:
            raise exceptions.NotFound()
        return Response({"code": code})
