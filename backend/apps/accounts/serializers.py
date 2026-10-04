from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.core.choices import Role
from apps.core.media.api import MediaPayload
from apps.core.media.services import asset_payload
from apps.core.models import Country, Currency

from . import selectors
from .models import GuestIdentity, User

LANGUAGE_CHOICES = [code for code, _name in settings.LANGUAGES]


class CodeRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(required=False, allow_blank=True, max_length=32)
    email = serializers.CharField(required=False, allow_blank=True, max_length=254)
    locale = serializers.ChoiceField(choices=LANGUAGE_CHOICES, required=False)

    def validate(self, attrs):
        if bool(attrs.get("phone")) == bool(attrs.get("email")):
            raise serializers.ValidationError(_("Enter a phone number or an e-mail address."))
        return attrs


class CodeRequestResultSerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    channel = serializers.ChoiceField(choices=["whatsapp", "sms", "email", "console"])
    resend_after = serializers.IntegerField(help_text="Seconds before a new code can be asked.")
    expires_in = serializers.IntegerField(help_text="Seconds before the code expires.")


class CodeVerifySerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    code = serializers.RegexField(r"^\d{6}$", error_messages={"invalid": _("Enter the 6 digits.")})
    locale = serializers.ChoiceField(choices=LANGUAGE_CHOICES, required=False)


class PasswordLoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class MeSerializer(serializers.ModelSerializer):
    country = serializers.SlugRelatedField(
        slug_field="code",
        queryset=Country.objects.filter(is_active=True),
        allow_null=True,
        required=False,
    )
    preferred_currency = serializers.SlugRelatedField(
        slug_field="code",
        queryset=Currency.objects.filter(is_active=True),
        allow_null=True,
        required=False,
    )
    phone = serializers.CharField(read_only=True, allow_null=True)
    email = serializers.EmailField(read_only=True, allow_null=True)
    birth_date = serializers.DateField(read_only=True, allow_null=True)
    photo = serializers.SerializerMethodField()
    has_password = serializers.SerializerMethodField()
    is_pro = serializers.SerializerMethodField()
    is_minor = serializers.SerializerMethodField()
    onboarding_required = serializers.SerializerMethodField()
    quiet_hours_start = serializers.TimeField(format="%H:%M", allow_null=True, required=False)
    quiet_hours_end = serializers.TimeField(format="%H:%M", allow_null=True, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "phone",
            "email",
            "first_name",
            "last_name",
            "birth_date",
            "city",
            "country",
            "preferred_language",
            "preferred_currency",
            "theme",
            "text_size",
            "data_saver",
            "audio_mode",
            "notify_whatsapp",
            "notify_email",
            "notify_push",
            "quiet_hours_start",
            "quiet_hours_end",
            "roles",
            "is_pro",
            "is_minor",
            "photo",
            "has_password",
            "onboarding_required",
            "created_at",
        ]
        read_only_fields = ["id", "roles", "created_at"]

    @extend_schema_field(MediaPayload)
    def get_photo(self, user):
        return asset_payload(user.photo)

    def get_has_password(self, user) -> bool:
        return user.has_usable_password()

    def get_is_pro(self, user) -> bool:
        return Role.PRO in user.roles

    def get_is_minor(self, user) -> bool:
        return selectors.is_minor(user)

    def get_onboarding_required(self, user) -> bool:
        return user.onboarded_at is None or user.birth_date is None


class SignInSerializer(serializers.Serializer):
    created = serializers.BooleanField()
    deletion_cancelled = serializers.BooleanField(
        help_text="The account was waiting to be deleted: signing in kept it."
    )
    user = MeSerializer()


class OnboardingSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=[Role.CLIENT, Role.PRO])
    birth_date = serializers.DateField()
    trades = serializers.ListField(
        child=serializers.SlugField(max_length=40), required=False, max_length=7
    )
    language = serializers.ChoiceField(choices=LANGUAGE_CHOICES, required=False)
    city = serializers.CharField(max_length=80, required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["mode"] == Role.PRO and not attrs.get("trades"):
            raise serializers.ValidationError({"trades": _("Choose at least one trade.")})
        return attrs


class ContactChangeRequestSerializer(CodeRequestSerializer):
    pass


class ContactChangeConfirmSerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    code = serializers.RegexField(r"^\d{6}$", error_messages={"invalid": _("Enter the 6 digits.")})


class PasswordSetSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=128, trim_whitespace=False)

    def validate_password(self, value):
        validate_password(value, self.context["request"].user)
        return value


class DeleteAccountSerializer(serializers.Serializer):
    confirm = serializers.BooleanField()

    def validate_confirm(self, value):
        if value is not True:
            raise serializers.ValidationError(_("Confirm that you want to delete your account."))
        return value


class DeletionScheduledSerializer(serializers.Serializer):
    erase_after = serializers.DateTimeField(
        help_text="Signing in again before this date keeps the account."
    )


class PhotoSerializer(serializers.Serializer):
    photo = serializers.FileField()


class GuestSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(max_length=32)

    class Meta:
        model = GuestIdentity
        fields = ["id", "first_name", "phone"]
        read_only_fields = ["id"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["phone"] = str(instance.phone)
        return data
