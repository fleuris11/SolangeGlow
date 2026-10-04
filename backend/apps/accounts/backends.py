import phonenumbers
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class PhoneOrEmailBackend(ModelBackend):
    """Authenticate with an e-mail address or a phone number and a password."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        identifier = (username or kwargs.get("email") or kwargs.get("phone") or "").strip()
        if not identifier or password is None:
            return None

        user = None
        if "@" in identifier:
            user = User.objects.filter(email__iexact=identifier).first()
        else:
            try:
                number = phonenumbers.parse(identifier, settings.PHONENUMBER_DEFAULT_REGION)
            except phonenumbers.NumberParseException:
                number = None
            if number is not None and phonenumbers.is_valid_number(number):
                e164 = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
                user = User.objects.filter(phone=e164).first()

        if user is None:
            # Run the hasher anyway to reduce timing differences between cases.
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
