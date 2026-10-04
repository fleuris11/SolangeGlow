from decimal import Decimal

import pytest

from apps.core.money import CurrencyMismatchError, Money, UnknownCurrencyError


@pytest.mark.parametrize(
    ("major", "currency", "minor"),
    [
        ("15000", "XOF", 15000),
        (Decimal("25.50"), "EUR", 2550),
        ("0.01", "eur", 1),
        (7, "EUR", 700),
    ],
)
def test_from_major_uses_currency_exponent(major, currency, minor):
    money = Money.from_major(major, currency)

    assert money.amount_minor == minor
    assert money.currency == currency.upper()


def test_from_major_rejects_too_many_decimals():
    with pytest.raises(ValueError):
        Money.from_major("10.5", "XOF")
    with pytest.raises(ValueError):
        Money.from_major("1.001", "EUR")


def test_floats_are_refused():
    with pytest.raises(TypeError):
        Money.from_major(1.5, "EUR")
    with pytest.raises(TypeError):
        Money(1.5, "EUR")  # type: ignore[arg-type]


def test_unknown_currency_is_refused():
    with pytest.raises(UnknownCurrencyError):
        Money(100, "ABC")


def test_to_major():
    assert Money(2550, "EUR").to_major() == Decimal("25.50")
    assert Money(15000, "XOF").to_major() == Decimal("15000")


def test_arithmetic_in_same_currency():
    a = Money(1000, "XOF")
    b = Money(250, "XOF")

    assert a + b == Money(1250, "XOF")
    assert a - b == Money(750, "XOF")
    assert -a == Money(-1000, "XOF")
    assert a * 3 == Money(3000, "XOF")
    assert 2 * b == Money(500, "XOF")
    assert b < a


def test_mixing_currencies_raises():
    with pytest.raises(CurrencyMismatchError):
        Money(100, "XOF") + Money(100, "EUR")
    with pytest.raises(CurrencyMismatchError):
        Money(100, "XOF") < Money(100, "EUR")  # noqa: B015


def test_percentage_rounds_half_up_to_minor_unit():
    assert Money(15000, "XOF").percentage("12.5") == Money(1875, "XOF")
    assert Money(999, "EUR").percentage(Decimal("10")) == Money(100, "EUR")
    assert Money(5, "XOF").percentage(10) == Money(1, "XOF")


@pytest.mark.parametrize(
    ("money", "locale", "expected"),
    [
        (Money(15000, "XOF"), "fr", "15\u202f000\u00a0FCFA"),
        (Money(2500, "EUR"), "fr", "25,00\u00a0€"),
        (Money(123456, "EUR"), "sk", "1\u202f234,56\u00a0€"),
        (Money(2500, "EUR"), "en", "€25.00"),
        (Money(15000, "XOF"), "en", "15,000 FCFA"),
        (Money(-2500, "EUR"), "fr", "-25,00\u00a0€"),
    ],
)
def test_format(money, locale, expected):
    assert money.format(locale) == expected
