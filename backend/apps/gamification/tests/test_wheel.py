# ruff: noqa: S311 - seeded generators check the distribution of the draw.
"""The Glow wheel: one free spin a day, never paid, no purchase needed; the draw follows
the weights of the admin and nothing else (no bias by person, day or history)."""

import datetime
import random
from collections import Counter

import pytest

from apps.core.models import FeatureFlag
from apps.gamification import errors
from apps.gamification.models import Voucher, WheelPrize, WheelSpin
from apps.gamification.services import points, wheel
from apps.messaging.tests.factories import adult, minor
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db
NOON = datetime.datetime(2026, 11, 2, 11, 0, tzinfo=datetime.UTC)


@pytest.fixture(autouse=True)
def prizes():
    WheelPrize.objects.all().delete()
    return [
        WheelPrize.objects.create(label="5 points", kind="points", points=5, weight=50, position=0),
        WheelPrize.objects.create(
            label="25 points", kind="points", points=25, weight=30, position=1
        ),
        WheelPrize.objects.create(
            label="-500 FCFA", kind="amount_off", amount_off_minor=500, weight=15, position=2
        ),
        WheelPrize.objects.create(label="A demain", kind="nothing", weight=5, position=3),
    ]


def chi_square(observed: Counter, expected: dict, total: int) -> float:
    return sum((observed[k] - total * p) ** 2 / (total * p) for k, p in expected.items())


def test_the_draw_follows_the_weights_and_nothing_else(prizes):
    """20 000 draws with a seeded generator: the frequencies match the weights (chi-square
    below the 99.9 % threshold for 3 degrees of freedom, 16.27)."""
    rng = random.Random(20261102)
    total = 20_000
    found = Counter(wheel.draw(prizes, rng).pk for _ in range(total))
    expected = {p.pk: p.weight / 100 for p in prizes}
    assert chi_square(found, expected, total) < 16.27
    assert set(found) == {p.pk for p in prizes}


def test_a_prize_at_weight_zero_never_comes_out(prizes):
    prizes[3].weight = 0
    prizes[3].save()
    awa = adult()
    shown = wheel.shown(awa)
    assert prizes[3] not in shown
    rng = random.Random(1)
    assert all(wheel.draw(shown, rng) != prizes[3] for _ in range(2000))


def test_the_chances_told_are_the_weights(prizes):
    odds = wheel.chances(prizes)
    assert [float(odds[p.pk]) for p in prizes] == [50.0, 30.0, 15.0, 5.0]


def test_the_draw_does_not_depend_on_the_person():
    """Same random numbers, two different people: the same prizes."""
    awa, fifame = adult(), adult("Fifamè")
    first = [
        wheel.draw(wheel.available(awa, NOON.date()), random.Random(seed)) for seed in range(50)
    ]
    second = [
        wheel.draw(wheel.available(fifame, NOON.date()), random.Random(seed)) for seed in range(50)
    ]
    assert first == second


def test_one_free_spin_a_day():
    awa = adult()
    spin = wheel.spin(awa, rng=random.Random(3), now=NOON)
    assert WheelSpin.objects.filter(user=awa).count() == 1
    with pytest.raises(errors.AlreadySpun):
        wheel.spin(awa, now=NOON + datetime.timedelta(hours=2))
    assert wheel.spin(awa, now=NOON + datetime.timedelta(days=1)).pk != spin.pk


def test_no_purchase_and_no_payment_ever():
    awa = adult()
    wheel.spin(awa, now=NOON)
    assert not Payment.objects.filter(buyer=awa).exists()
    assert not Payment.objects.exists()


class Fixed:
    """A generator that always draws the same ticket."""

    def __init__(self, ticket):
        self.ticket = ticket

    def randrange(self, total):
        return self.ticket % total


def test_points_and_voucher_prizes():
    awa = adult()
    spin = wheel.spin(awa, rng=Fixed(60), now=NOON)  # 50 + 10: the second slice
    assert (spin.label, spin.points) == ("25 points", 25)
    assert points.balance(awa) == 25
    fifame = adult("Fifamè")
    won = wheel.spin(fifame, rng=Fixed(85), now=NOON)  # the discount
    assert won.voucher.kind == Voucher.Kind.AMOUNT_OFF
    assert won.voucher.amount_off_minor == 500
    assert won.voucher.code.startswith("GLOW-")


def test_a_minor_never_gets_a_voucher(prizes):
    lina = minor()
    available = wheel.available(lina, NOON.date())
    assert prizes[2] not in available
    spins = {wheel.draw(available, random.Random(s)).kind for s in range(300)}
    assert "amount_off" not in spins


def test_a_prize_out_of_stock_today_leaves_the_draw(prizes):
    prizes[2].daily_stock = 1
    prizes[2].save()
    awa, fifame = adult(), adult("Fifamè")
    wheel.spin(awa, rng=Fixed(85), now=NOON)
    assert prizes[2] not in wheel.available(fifame, NOON.date())
    # Tomorrow it is back.
    assert prizes[2] in wheel.available(fifame, NOON.date() + datetime.timedelta(days=1))


def test_prizes_of_another_country(prizes):
    prizes[2].countries = ["BJ"]
    prizes[2].save()
    from apps.core.tests.factories import CountryFactory, CurrencyFactory

    france = CountryFactory(
        code="FR",
        name="France",
        phone_prefix="+33",
        timezone="Europe/Paris",
        default_currency=CurrencyFactory(code="EUR", name="Euro", symbol="€", decimal_places=2),
    )
    grace = adult("Grâce", country=france)
    assert prizes[2] not in wheel.shown(grace)
    assert prizes[2] in wheel.shown(adult())


def test_the_wheel_switched_off_in_a_country():
    FeatureFlag.objects.filter(key="wheel").update(is_enabled=False)
    with pytest.raises(errors.WheelUnavailable):
        wheel.spin(adult(), now=NOON)


def test_no_prize_at_all():
    WheelPrize.objects.update(is_active=False)
    with pytest.raises(errors.NoPrize):
        wheel.spin(adult(), now=NOON)
    assert wheel.state(adult("Fifamè"))["can_spin"] is False
