"""« Buy this product » on a post: the shop module registers how to check and show a
product (no import of the shop here, the shop depends on social)."""

from __future__ import annotations

from collections.abc import Callable

_owns: Callable[[object, object], bool] | None = None
_card: Callable[[object], dict | None] | None = None


def register(owns: Callable[[object, object], bool], card: Callable[[object], dict | None]):
    global _owns, _card
    _owns, _card = owns, card


def unregister() -> None:
    global _owns, _card
    _owns, _card = None, None


def owns(author, product_id) -> bool:
    """The product is the author's own and on sale (no shop: never)."""
    return _owns is not None and _owns(author, product_id)


def card(product_id) -> dict | None:
    """What the post shows: name, price, picture, link; None when not on sale any more."""
    if _card is None or product_id is None:
        return None
    return _card(product_id)
