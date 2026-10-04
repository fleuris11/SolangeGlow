from django.db import models
from django.utils.translation import gettext_lazy as _


class Role(models.TextChoices):
    """Platform roles. A user can hold several of them."""

    CLIENT = "client", _("Client")
    PRO = "pro", _("Professional")
    STAFF = "staff", _("Staff")
