"""Business logic of the Diaspora gifts (module 9, ADR-014).

- `quote`, `offer`, `start_payment`: the giver chooses, pays in euros
- `send_due`, `send`, `resend`: the person receives her link on the chosen day
- `open_gift`, `book`, `receive`, `as_card`, `claim`: the person uses her gift
- `pay_with_card`, `cover_deposit`: a Glow gift card pays a purchase in Benin
- `cancel`, `expire`, `remind`: refunded while unused, over after its date
- `add_photo`, `answer`: the proof of joy, sent only with her yes
"""

from .offering import (
    Quote,
    cancel,
    expire,
    may_cancel_payment,
    offer,
    on_payment_change,
    quote,
    remind,
    resend,
    send,
    send_due,
    start_payment,
)
from .proof import add_photo, answer, candidates, on_completed
from .using import (
    as_card,
    book,
    by_token,
    card_by_code,
    claim,
    cover_deposit,
    credit_back,
    is_giver,
    open_gift,
    pay_with_card,
    receive,
)

__all__ = [
    "Quote",
    "add_photo",
    "answer",
    "as_card",
    "book",
    "by_token",
    "cancel",
    "candidates",
    "card_by_code",
    "claim",
    "cover_deposit",
    "credit_back",
    "expire",
    "is_giver",
    "may_cancel_payment",
    "offer",
    "on_completed",
    "on_payment_change",
    "open_gift",
    "pay_with_card",
    "quote",
    "receive",
    "remind",
    "resend",
    "send",
    "send_due",
    "start_payment",
]
