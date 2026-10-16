"""Sale price in FCFA of a product bought in France (specification, module 6):

    P_FCFA = [(P_purchase + p x T_kg + E) x (1 + D) x (1 + M) + F] x 655.957

rounded up to the next hundred FCFA. P_purchase, T_kg, E and F in euros, p in kg, D the
estimated customs rate, M the margin. Every parameter is set per category in the admin;
an empty one takes the default of the settings. Computed with exact decimals, stored as
integers.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal

from apps.core.selectors import get_setting

DEFAULTS = {
    "transport_per_kg_cents": 1200,
    "express_per_kg_cents": 2500,
    "packaging_cents": 150,
    "customs_bps": 2000,
    "margin_bps": 2500,
    "payment_fee_cents": 80,
}
FIELDS = tuple(DEFAULTS)
CENT = Decimal(100)
BPS = Decimal(10_000)


@dataclass(frozen=True)
class Params:
    transport_per_kg_cents: int
    express_per_kg_cents: int
    packaging_cents: int
    customs_bps: int
    margin_bps: int
    payment_fee_cents: int


@dataclass(frozen=True)
class Breakdown:
    """Each step of the formula, in euros (exact), then the rounded price in FCFA."""

    purchase: Decimal
    transport: Decimal
    packaging: Decimal
    subtotal: Decimal
    with_customs: Decimal
    with_margin: Decimal
    payment_fee: Decimal
    total_eur: Decimal
    rate: Decimal
    exact_xof: Decimal
    price_xof: int


def params_for(category=None) -> Params:
    defaults = {**DEFAULTS, **(get_setting("selection.pricing_defaults", default={}) or {})}
    values = {}
    for field in FIELDS:
        own = getattr(category, field, None) if category is not None else None
        values[field] = int(own if own is not None else defaults[field])
    return Params(**values)


def rate() -> Decimal:
    return Decimal(str(get_setting("selection.eur_xof_rate", default="655.957")))


def compute(
    purchase_cents: int,
    weight_grams: int,
    params: Params,
    *,
    express: bool = False,
    eur_xof: Decimal | None = None,
    rounding: int | None = None,
) -> Breakdown:
    eur_xof = eur_xof if eur_xof is not None else rate()
    rounding = rounding or int(get_setting("selection.rounding_xof", default=100))
    per_kg = params.express_per_kg_cents if express else params.transport_per_kg_cents
    purchase = Decimal(purchase_cents) / CENT
    transport = Decimal(weight_grams) / Decimal(1000) * Decimal(per_kg) / CENT
    packaging = Decimal(params.packaging_cents) / CENT
    subtotal = purchase + transport + packaging
    with_customs = subtotal * (1 + Decimal(params.customs_bps) / BPS)
    with_margin = with_customs * (1 + Decimal(params.margin_bps) / BPS)
    fee = Decimal(params.payment_fee_cents) / CENT
    total = with_margin + fee
    exact = total * eur_xof
    steps = (exact / rounding).to_integral_value(rounding=ROUND_CEILING)
    return Breakdown(
        purchase=purchase,
        transport=transport,
        packaging=packaging,
        subtotal=subtotal,
        with_customs=with_customs,
        with_margin=with_margin,
        payment_fee=fee,
        total_eur=total,
        rate=eur_xof,
        exact_xof=exact,
        price_xof=int(steps) * rounding,
    )


def express_allowed(category) -> bool:
    """Air-restricted goods never go by express (and are blocked by default)."""
    return not category.air_restricted


def price_of(product, *, express: bool = False) -> Breakdown:
    return compute(
        product.purchase_price_cents,
        product.weight_grams,
        params_for(product.category),
        express=express,
    )
