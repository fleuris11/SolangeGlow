"""Money value object.

Amounts are always integers in the smallest unit of the currency (`amount_minor`):
XOF has no decimals (1 = 1 FCFA), EUR has two (1 = 0.01 EUR). Never use floats.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

# ISO 4217 minor-unit exponents. This is reference data, not a business parameter.
CURRENCY_EXPONENTS: dict[str, int] = {
    "XOF": 0,
    "XAF": 0,
    "EUR": 2,
    "USD": 2,
    "GBP": 2,
    "CHF": 2,
    "CAD": 2,
}

CURRENCY_SYMBOLS: dict[str, str] = {
    "XOF": "FCFA",
    "XAF": "FCFA",
    "EUR": "€",
    "USD": "$",
    "GBP": "£",
}

NARROW_NBSP = "\u202f"
NBSP = "\u00a0"


class CurrencyMismatchError(ValueError):
    """Raised when combining amounts expressed in different currencies."""


class UnknownCurrencyError(ValueError):
    """Raised for a currency code without a known minor-unit exponent."""


def currency_exponent(currency: str) -> int:
    try:
        return CURRENCY_EXPONENTS[currency.upper()]
    except KeyError as exc:
        raise UnknownCurrencyError(currency) from exc


@dataclass(frozen=True, slots=True)
class Money:
    amount_minor: int
    currency: str

    def __post_init__(self) -> None:
        if isinstance(self.amount_minor, bool) or not isinstance(self.amount_minor, int):
            raise TypeError("amount_minor must be an int")
        code = self.currency.upper()
        currency_exponent(code)
        object.__setattr__(self, "currency", code)

    # --- Construction -------------------------------------------------------

    @classmethod
    def zero(cls, currency: str) -> Money:
        return cls(0, currency)

    @classmethod
    def from_major(cls, amount: Decimal | int | str, currency: str) -> Money:
        """Build from a human amount ("25.50" EUR -> 2550). Rejects sub-unit precision."""
        if isinstance(amount, float):
            raise TypeError("floats are not allowed for money, use Decimal or str")
        try:
            value = Decimal(amount)
        except InvalidOperation as exc:
            raise ValueError(f"invalid amount: {amount!r}") from exc
        scaled = value.scaleb(currency_exponent(currency))
        if scaled != scaled.to_integral_value():
            raise ValueError(f"{amount} has too many decimals for {currency}")
        return cls(int(scaled), currency)

    # --- Conversion ---------------------------------------------------------

    @property
    def exponent(self) -> int:
        return currency_exponent(self.currency)

    def to_major(self) -> Decimal:
        return Decimal(self.amount_minor).scaleb(-self.exponent)

    # --- Arithmetic ---------------------------------------------------------

    def _check(self, other: object) -> Money:
        if not isinstance(other, Money):
            raise TypeError(f"cannot combine Money with {type(other).__name__}")
        if other.currency != self.currency:
            raise CurrencyMismatchError(f"{self.currency} != {other.currency}")
        return other

    def __add__(self, other: Money) -> Money:
        return Money(self.amount_minor + self._check(other).amount_minor, self.currency)

    def __sub__(self, other: Money) -> Money:
        return Money(self.amount_minor - self._check(other).amount_minor, self.currency)

    def __neg__(self) -> Money:
        return Money(-self.amount_minor, self.currency)

    def __mul__(self, factor: int) -> Money:
        if isinstance(factor, bool) or not isinstance(factor, int):
            return NotImplemented
        return Money(self.amount_minor * factor, self.currency)

    __rmul__ = __mul__

    def __lt__(self, other: Money) -> bool:
        return self.amount_minor < self._check(other).amount_minor

    def __le__(self, other: Money) -> bool:
        return self.amount_minor <= self._check(other).amount_minor

    def __gt__(self, other: Money) -> bool:
        return self.amount_minor > self._check(other).amount_minor

    def __ge__(self, other: Money) -> bool:
        return self.amount_minor >= self._check(other).amount_minor

    def __bool__(self) -> bool:
        return self.amount_minor != 0

    def percentage(self, rate: Decimal | str | int) -> Money:
        """Return `rate` percent of this amount, rounded half up to the minor unit."""
        if isinstance(rate, float):
            raise TypeError("floats are not allowed for rates, use Decimal or str")
        value = Decimal(self.amount_minor) * Decimal(rate) / Decimal(100)
        return Money(int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP)), self.currency)

    # --- Display ------------------------------------------------------------

    def format(self, locale: str = "fr") -> str:
        """Human display: "15 000 FCFA", "25,00 €" (fr/sk) or "€25.00" (en)."""
        lang = locale.split("-")[0].lower()
        major = self.to_major()
        sign = "-" if major < 0 else ""
        integer, _, fraction = f"{abs(major):.{self.exponent}f}".partition(".")
        symbol = CURRENCY_SYMBOLS.get(self.currency, self.currency)

        if lang == "en":
            grouped = f"{int(integer):,}"
            number = f"{grouped}.{fraction}" if fraction else grouped
            if len(symbol) == 1:
                return f"{sign}{symbol}{number}"
            return f"{sign}{number} {symbol}"

        grouped = f"{int(integer):,}".replace(",", NARROW_NBSP)
        number = f"{grouped},{fraction}" if fraction else grouped
        return f"{sign}{number}{NBSP}{symbol}"

    def __str__(self) -> str:
        return f"{self.to_major()} {self.currency}"
