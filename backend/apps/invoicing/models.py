"""Invoices and receipts with continuous numbering per issuer and per year.

An issued document never changes and is never deleted: a mistake is corrected by a credit
note. Only the sending to an approved e-invoicing platform is updated afterwards.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class Issuer(BaseModel):
    """Who issues the documents: a pro (her legal details), or the platform itself."""

    pro = models.OneToOneField(
        "pros.ProProfile",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="issuer",
        verbose_name=_("pro"),
    )
    is_platform = models.BooleanField(_("the platform"), default=False)
    legal_name = models.CharField(_("legal name"), max_length=150, blank=True)
    address = models.CharField(_("address"), max_length=255, blank=True)
    country = models.ForeignKey(
        "core.Country", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    registration = models.CharField(
        _("company number"),
        max_length=40,
        blank=True,
        help_text=_("SIRET in France, IFU in Benin."),
    )
    vat_number = models.CharField(_("VAT number"), max_length=40, blank=True)
    vat_rate_bps = models.PositiveIntegerField(
        _("VAT rate"), default=0, help_text=_("In hundredths of a percent: 2000 = 20 %. 0: no VAT.")
    )
    vat_mention = models.CharField(
        _("VAT mention"),
        max_length=150,
        blank=True,
        help_text=_("For example « TVA non applicable, art. 293 B du CGI »."),
    )
    footer = models.CharField(_("footer"), max_length=255, blank=True)

    class Meta:
        verbose_name = _("invoice issuer")
        verbose_name_plural = _("invoice issuers")
        constraints = [
            models.UniqueConstraint(
                fields=["is_platform"],
                condition=models.Q(is_platform=True),
                name="invoicing_one_platform_issuer",
            )
        ]

    def __str__(self):
        return self.legal_name or str(self.pro or _("Platform"))


class Sequence(BaseModel):
    """The next number of a series (locked while a document takes it: no gap, no double)."""

    issuer = models.ForeignKey(Issuer, on_delete=models.CASCADE, related_name="sequences")
    prefix = models.CharField(max_length=2)
    year = models.PositiveSmallIntegerField()
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["issuer", "prefix", "year"], name="invoicing_one_sequence"
            )
        ]


class Document(BaseModel):
    class Kind(models.TextChoices):
        INVOICE = "invoice", _("Invoice")
        RECEIPT = "receipt", _("Receipt")
        CREDIT_NOTE = "credit_note", _("Credit note")

    class EInvoice(models.TextChoices):
        NOT_SENT = "not_sent", _("Not sent")
        SENT = "sent", _("Sent to the platform")
        FAILED = "failed", _("Not accepted")

    issuer = models.ForeignKey(
        Issuer, on_delete=models.PROTECT, related_name="documents", verbose_name=_("issuer")
    )
    kind = models.CharField(_("type"), max_length=12, choices=Kind.choices)
    number = models.CharField(_("number"), max_length=24)
    issued_at = models.DateTimeField(_("issued at"))
    buyer_name = models.CharField(_("client"), max_length=150)
    buyer_details = models.CharField(_("client details"), max_length=255, blank=True)
    buyer_user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("client account"),
    )
    lines = models.JSONField(_("lines"), default=list)
    currency = models.CharField(_("currency"), max_length=3)
    total_minor = models.BigIntegerField(_("total, taxes included"))
    tax_minor = models.BigIntegerField(_("of which VAT"), default=0)
    paid_with = models.CharField(_("paid with"), max_length=60, blank=True)
    source_type = models.CharField(max_length=20, blank=True)
    source_id = models.UUIDField(null=True, blank=True)
    corrects = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="credit_notes",
        verbose_name=_("corrects"),
    )
    einvoice_status = models.CharField(
        _("electronic invoice"), max_length=10, choices=EInvoice.choices, default=EInvoice.NOT_SENT
    )
    einvoice_reference = models.CharField(max_length=80, blank=True)

    MUTABLE = {"einvoice_status", "einvoice_reference", "updated_at"}

    class Meta:
        verbose_name = _("invoice or receipt")
        verbose_name_plural = _("invoices and receipts")
        ordering = ["-issued_at"]
        constraints = [
            models.UniqueConstraint(fields=["issuer", "number"], name="invoicing_unique_number")
        ]

    def __str__(self):
        return self.number

    def save(self, *args, **kwargs):
        fields = kwargs.get("update_fields")
        if not self._state.adding and (fields is None or set(fields) - self.MUTABLE):
            raise ValueError("An issued document cannot change: issue a credit note.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("An issued document cannot be deleted: issue a credit note.")
