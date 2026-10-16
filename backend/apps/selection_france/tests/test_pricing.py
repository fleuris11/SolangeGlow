"""The price formula of the specification, with worked examples (all in FCFA).

P = [(purchase + kg x transport + packaging) x (1 + customs) x (1 + margin) + fees] x 655.957,
rounded up to the next hundred.
"""

from decimal import Decimal

import pytest

from apps.core.tests.factories import PlatformSettingFactory
from apps.selection_france import pricing, services
from apps.selection_france.models import SelectionProduct

from .factories import category, product

pytestmark = pytest.mark.django_db

# Defaults: 12 €/kg grouped, 25 €/kg express, packaging 1.50 €, customs 20 %, margin 25 %,
# payment fees 0.80 €.
PARAMS = pricing.Params(
    transport_per_kg_cents=1200,
    express_per_kg_cents=2500,
    packaging_cents=150,
    customs_bps=2000,
    margin_bps=2500,
    payment_fee_cents=80,
)


def test_worked_example_grouped():
    # (20 + 0.3 x 12 + 1.50) = 25.10 ; x 1.20 = 30.12 ; x 1.25 = 37.65 ; + 0.80 = 38.45 €
    # 38.45 x 655.957 = 25 221.55 FCFA -> 25 300 FCFA
    b = pricing.compute(2000, 300, PARAMS)
    assert b.subtotal == Decimal("25.10")
    assert b.with_customs == Decimal("30.1200")
    assert b.with_margin == Decimal("37.650000")
    assert b.total_eur == Decimal("38.450000")
    assert b.exact_xof.quantize(Decimal("0.01")) == Decimal("25221.55")
    assert b.price_xof == 25_300


def test_worked_example_express():
    # (20 + 0.3 x 25 + 1.50) = 29 ; x 1.2 x 1.25 = 43.50 ; + 0.80 = 44.30 € -> 29 058.90 -> 29 100
    assert pricing.compute(2000, 300, PARAMS, express=True).price_xof == 29_100


@pytest.mark.parametrize(
    ("purchase", "grams", "expected"),
    [
        # a mini format: 4.99 + 0.60 + 1.50 = 7.09 -> 11.435 € -> 7 500.87 -> 7 600
        (499, 50, 7_600),
        # a hair dryer: 89 + 14.40 + 1.50 = 104.90 -> 158.15 € -> 103 739.60 -> 103 800
        (8900, 1_200, 103_800),
        # almost free: 0.01 + 1.50 = 1.51 -> 3.065 € -> 2 010.51 -> 2 100
        (1, 0, 2_100),
    ],
)
def test_more_cases(purchase, grams, expected):
    assert pricing.compute(purchase, grams, PARAMS).price_xof == expected


def test_a_price_already_on_a_hundred_stays():
    # 38.45 € x 2000 = 76 900 exactly: nothing to round.
    assert pricing.compute(2000, 300, PARAMS, eur_xof=Decimal(2000)).price_xof == 76_900
    assert pricing.compute(2000, 300, PARAMS, eur_xof=Decimal(1000)).price_xof == 38_500


def test_category_parameters_replace_the_defaults():
    fragrance = category("fragrance")
    assert fragrance.margin_bps == 3000 and fragrance.air_restricted
    params = pricing.params_for(fragrance)
    assert params.margin_bps == 3000 and params.customs_bps == 2000
    assert pricing.params_for(None) == PARAMS


def test_defaults_and_rounding_come_from_the_settings():
    PlatformSettingFactory(
        key="selection.pricing_defaults", value='{"margin_bps": 0}', value_type="json"
    )
    PlatformSettingFactory(key="selection.rounding_xof", value="500")
    params = pricing.params_for(None)
    assert params.margin_bps == 0 and params.transport_per_kg_cents == 1200
    # 30.12 + 0.80 = 30.92 € x 655.957 = 20 282.19 -> next 500: 20 500
    assert pricing.compute(2000, 300, params).price_xof == 20_500


def test_a_product_is_priced_and_repriced():
    item = product()
    assert (item.price_xof, item.express_price_xof) == (25_300, 29_100) and item.priced_at
    makeup = category()
    makeup.margin_bps = 0
    makeup.save()
    assert services.reprice_all(SelectionProduct.objects.all()) == 1
    item.refresh_from_db()
    assert item.price_xof == 20_300  # 30.92 € x 655.957 = 20 282.19 -> 20 300


def test_no_express_for_goods_forbidden_by_air():
    perfume = product(slug="parfum", category=category("fragrance"))
    assert perfume.express_price_xof is None and perfume.price_xof > 0
