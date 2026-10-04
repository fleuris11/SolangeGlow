from django.conf import settings
from django.urls import path

from . import views

urlpatterns = [
    path("auth/otp/request", views.CodeRequestView.as_view(), name="otp-request"),
    path("auth/otp/verify", views.CodeVerifyView.as_view(), name="otp-verify"),
    path("auth/password/login", views.PasswordLoginView.as_view(), name="password-login"),
    path("auth/refresh", views.RefreshView.as_view(), name="token-refresh"),
    path("auth/logout", views.LogoutView.as_view(), name="logout"),
    path("auth/logout-all", views.LogoutAllView.as_view(), name="logout-all"),
    path("me", views.MeView.as_view(), name="me"),
    path("me/photo", views.PhotoView.as_view(), name="me-photo"),
    path("me/contact", views.ContactChangeRequestView.as_view(), name="me-contact"),
    path(
        "me/contact/confirm",
        views.ContactChangeConfirmView.as_view(),
        name="me-contact-confirm",
    ),
    path("me/password", views.PasswordView.as_view(), name="me-password"),
    path("me/onboarding", views.OnboardingView.as_view(), name="me-onboarding"),
    path("guest", views.GuestView.as_view(), name="guest"),
]

if settings.ACCOUNTS_DEV_OTP_ENDPOINT:
    urlpatterns.append(path("dev/last-code", views.DevLastCodeView.as_view(), name="dev-last-code"))
