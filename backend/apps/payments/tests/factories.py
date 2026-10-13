"""People and payments for the tests. Example used everywhere (ADR-007):
items 10 000 FCFA + delivery 1 000, buyer protection 3 % = 330, total 11 330;
with a 5 % commission rule: commission 500 on the items."""

import datetime

from django.utils import timezone

from apps.core.media.models import MediaAsset
from apps.messaging.tests.factories import adult
from apps.payments import ledger, services
from apps.payments.models import LedgerAccount, Payment, PricingRule
from apps.pros.models import ProProfile
from apps.pros.tests.factories import ProFactory

Kind = LedgerAccount.Kind


def seller(name="Aïcha Tresses", **kwargs):
    kwargs.setdefault("verification_status", ProProfile.Verification.VERIFIED)
    return ProFactory(business_name=name, user=adult(name.split()[0]), **kwargs).user


def commission(percent_bps=500, **kwargs):
    return PricingRule.objects.create(
        kind=PricingRule.Kind.COMMISSION,
        name=f"Commission {percent_bps}",
        percent_bps=percent_bps,
        **kwargs,
    )


def payment(buyer=None, sold_by=None, **kwargs) -> Payment:
    values = {
        "purpose": "order",
        "items_minor": 10_000,
        "delivery_minor": 1_000,
        "currency": "XOF",
        "description": "Perruque lace frontale",
    }
    values.update(kwargs)
    return services.create_payment(buyer or adult("Awa"), sold_by or seller(), **values)


def paid(p: Payment | None = None, **kwargs) -> Payment:
    p = p or payment(**kwargs)
    services.mark_paid(p, amount_minor=p.total_minor, currency=p.currency, key=f"test:{p.pk}")
    p.refresh_from_db()
    return p


def shipped(p: Payment | None = None, **kwargs) -> Payment:
    p = paid(p, **kwargs)
    services.ship(p, actor=p.seller, carrier="Gozem", tracking_number="GZ-1")
    p.refresh_from_db()
    return p


def code_of(p: Payment) -> str:
    return services.receipt_code_for(p, p.buyer)


def picture(owner, purpose="delivery_proof", status=MediaAsset.Status.READY) -> MediaAsset:
    return MediaAsset.objects.create(
        owner=owner,
        kind="image",
        purpose=purpose,
        visibility="private",
        status=status,
        variants={"medium": {"path": "image/x/medium.webp"}},
    )


def balances(p: Payment) -> dict:
    """Balances of the accounts touched by this payment (all money, not only this one)."""
    currency = p.currency
    return {
        "cash": ledger.balance_of(Kind.PROVIDER_CASH, currency),
        "seller_pending": ledger.balance_of(Kind.SELLER_PENDING, currency, owner=p.seller),
        "fees_pending": ledger.balance_of(Kind.FEES_PENDING, currency),
        "seller_available": ledger.balance_of(Kind.SELLER_AVAILABLE, currency, owner=p.seller),
        "commissions": ledger.balance_of(Kind.COMMISSION_REVENUE, currency),
        "protection": ledger.balance_of(Kind.FEE_REVENUE, currency),
        "refunds": ledger.balance_of(Kind.REFUNDS_IN_TRANSIT, currency),
        "payouts": ledger.balance_of(Kind.PAYOUTS_IN_TRANSIT, currency),
        "fees": ledger.balance_of(Kind.PROVIDER_FEES, currency),
    }


def later(**kwargs):
    return timezone.now() + datetime.timedelta(**kwargs)
