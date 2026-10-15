"""Business logic of the secure payment (ADR-007). Other modules call these functions:

- `create_payment`, `start_checkout`: an order, a booking deposit, a training…
- `ship`, `mark_delivered`, `confirm_receipt`, `cancel`: the life of the order
- `release`, `refund_full`, `refund_partial`: the outcomes
- `open_dispute`, `decide`: disputes
- `request_payout`: the seller takes her money
- `create_group`, `start_group_checkout`: a cart of several shops paid in one go
- `buyer_fee`: the buyer protection shown before ordering
- `listen(source_type, callback, may_cancel=)`: hear about every change of status
"""

from .common import can_move, forget, listen, may_cancel
from .disputes import add_evidence, decide, open_dispute
from .groups import create_group, group_status, start_group_checkout
from .payments import (
    buyer_fee,
    cancel,
    confirm_receipt,
    courier_token,
    create_payment,
    mark_delivered,
    mark_not_paid,
    mark_paid,
    payment_for_courier,
    receipt_code_for,
    refund_full,
    refund_partial,
    release,
    renew_receipt_code,
    ship,
    start_checkout,
)
from .payouts import request_payout, save_payout_method
from .refunds import mark_done_by_hand
from .tax import save_tax_profile

__all__ = [
    "add_evidence",
    "buyer_fee",
    "can_move",
    "cancel",
    "confirm_receipt",
    "courier_token",
    "create_group",
    "create_payment",
    "decide",
    "forget",
    "group_status",
    "listen",
    "mark_delivered",
    "mark_done_by_hand",
    "mark_not_paid",
    "mark_paid",
    "may_cancel",
    "open_dispute",
    "payment_for_courier",
    "receipt_code_for",
    "refund_full",
    "refund_partial",
    "release",
    "renew_receipt_code",
    "request_payout",
    "save_payout_method",
    "save_tax_profile",
    "ship",
    "start_checkout",
    "start_group_checkout",
]
