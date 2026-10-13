"""Tax data of the sellers and the yearly DAC7 figures (France: what sellers earned)."""

from __future__ import annotations

from collections import defaultdict

from django.db.models import Q

from apps.core import crypto
from apps.core.audit.services import record

from ..models import Payment, SellerTaxProfile


def save_tax_profile(seller, **values) -> SellerTaxProfile:
    tax_id = (values.pop("tax_id", "") or "").strip()
    profile, _ = SellerTaxProfile.objects.get_or_create(
        seller=seller, defaults={"legal_name": "", "address": "", "city": "", "country": ""}
    )
    for field, value in values.items():
        setattr(profile, field, value)
    if tax_id:
        profile.tax_id_secret = crypto.encrypt(tax_id)
        profile.tax_id_hint = f"•••• {tax_id[-4:]}"
    profile.save()
    record("payments.tax_profile_saved", profile, actor=seller)
    return profile


def tax_id_of(profile: SellerTaxProfile) -> str:
    return crypto.decrypt(profile.tax_id_secret) or "" if profile.tax_id_secret else ""


def dac7_rows(year: int) -> list[dict]:
    """Per seller and quarter: what she kept (after refunds), number of sales, commissions.

    A sale counts on the day it closed (paid to the seller or partly refunded).
    """
    closed = (
        Payment.objects.filter(
            Q(status=Payment.Status.RELEASED, released_at__year=year)
            | Q(status=Payment.Status.PARTIALLY_REFUNDED, refunded_at__year=year)
        )
        .select_related("seller")
        .order_by("seller_id")
    )
    totals = defaultdict(lambda: defaultdict(lambda: {"amount": 0, "count": 0, "fees": 0}))
    sellers = {}
    for payment in closed:
        when = payment.released_at or payment.refunded_at
        quarter = (when.month - 1) // 3 + 1
        cell = totals[(payment.seller_id, payment.currency)][quarter]
        cell["amount"] += payment.seller_gross_minor - payment.refunded_minor
        cell["count"] += 1
        cell["fees"] += payment.commission_minor
        sellers[payment.seller_id] = payment.seller
    profiles = {
        p.seller_id: p for p in SellerTaxProfile.objects.filter(seller_id__in=sellers.keys())
    }
    rows = []
    for (seller_id, currency), quarters in totals.items():
        profile = profiles.get(seller_id)
        row = {
            "seller_id": str(seller_id),
            "legal_name": profile.legal_name if profile else "",
            "is_business": profile.is_business if profile else "",
            "birth_date": profile.birth_date.isoformat() if profile and profile.birth_date else "",
            "address": profile.address if profile else "",
            "postal_code": profile.postal_code if profile else "",
            "city": profile.city if profile else "",
            "country": profile.country if profile else "",
            "tax_id": tax_id_of(profile) if profile else "",
            "vat_number": profile.vat_number if profile else "",
            "currency": currency,
        }
        for quarter in (1, 2, 3, 4):
            cell = quarters[quarter]
            row[f"q{quarter}_amount_minor"] = cell["amount"]
            row[f"q{quarter}_sales"] = cell["count"]
            row[f"q{quarter}_commissions_minor"] = cell["fees"]
        rows.append(row)
    return rows
