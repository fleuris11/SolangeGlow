from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class Trade(BaseModel):
    """A beauty or fashion trade (makeup, braids…). The list is edited in the admin."""

    class Icon(models.TextChoices):
        MAKEUP = "makeup", _("Lipstick")
        HAIR = "hair", _("Comb")
        BRAIDS = "braids", _("Braid")
        NAILS = "nails", _("Nail polish")
        SEWING = "sewing", _("Thread spool")
        HEADWRAP = "headwrap", _("Headwrap")
        SKINCARE = "skincare", _("Cream jar")

    key = models.SlugField(_("key"), max_length=40, unique=True)
    name = models.CharField(_("name"), max_length=80)
    icon = models.CharField(_("pictogram"), max_length=20, choices=Icon.choices)
    position = models.PositiveSmallIntegerField(_("position"), default=0)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("trade")
        verbose_name_plural = _("trades")
        ordering = ["position", "key"]

    def __str__(self):
        return self.name


class ProProfile(BaseModel):
    """Professional side of an account. A person can be client and pro with one account."""

    class Kind(models.TextChoices):
        INDEPENDENT = "independent", _("Independent")
        BUSINESS = "business", _("Salon or business")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pro_profile",
        verbose_name=_("account"),
    )
    kind = models.CharField(
        _("type"), max_length=12, choices=Kind.choices, default=Kind.INDEPENDENT
    )
    trades = models.ManyToManyField(
        Trade, blank=True, related_name="pros", verbose_name=_("trades")
    )

    class Meta:
        verbose_name = _("pro profile")
        verbose_name_plural = _("pro profiles")

    def __str__(self):
        return str(self.user)
