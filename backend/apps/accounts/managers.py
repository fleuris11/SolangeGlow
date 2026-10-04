from django.contrib.auth.base_user import BaseUserManager

from apps.core.choices import Role


def normalize_email(email: str | None) -> str | None:
    """Lowercase the whole address; return None for an empty value."""
    email = (email or "").strip().lower()
    return email or None


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email=None, phone=None, password=None, **extra_fields):
        email = normalize_email(email)
        phone = phone or None
        if not email and not phone:
            raise ValueError("A user needs a phone number or an e-mail address.")
        user = self.model(email=email, phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            # No password yet: sign-in will happen with a one-time code (OTP, coming soon).
            user.set_unusable_password()
        user.full_clean(exclude=["password"])
        user.save(using=self._db)
        return user

    def create_user(self, email=None, phone=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, phone, password, **extra_fields)

    def create_superuser(self, email=None, phone=None, password=None, **extra_fields):
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        extra_fields.setdefault("roles", [Role.CLIENT, Role.STAFF])
        return self._create_user(email, phone, password, **extra_fields)
