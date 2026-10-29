"""What points buy: a discount or free express shipping on the France Selection (the
platform sells, the platform pays the discount), or a course of the platform."""

from __future__ import annotations

import datetime

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone, translation

from apps.accounts.selectors import can_purchase
from apps.core.audit.services import record
from apps.core.money import Money

from .. import errors
from ..models import LEVEL_ORDER, Level, Reward, Voucher
from . import points
from .common import country_code, new_code, profile_of, require_games, setting

SELECTION = "selection_order"


def _language(user) -> str:
    return getattr(user, "preferred_language", "") or "fr"


def voucher_label(kind: str, amount_minor: int, language: str) -> str:
    with translation.override(language):
        if kind == Voucher.Kind.EXPRESS:
            return str(Voucher.Kind.EXPRESS.label)
        return translation.gettext("%(amount)s off the France Selection") % {
            "amount": Money(amount_minor, "XOF").format(language)
        }


def create_voucher(user, *, kind: str, origin: str, amount_minor: int = 0, days: int) -> Voucher:
    while True:
        try:
            with transaction.atomic():
                return Voucher.objects.create(
                    user=user,
                    kind=kind,
                    origin=origin,
                    code=f"GLOW-{new_code(6)}",
                    label=voucher_label(kind, amount_minor, _language(user))[:120],
                    amount_off_minor=amount_minor if kind == Voucher.Kind.AMOUNT_OFF else 0,
                    expires_at=timezone.now() + datetime.timedelta(days=max(1, days)),
                )
        except IntegrityError:
            continue  # the same code twice: draw another one


def usable(user):
    return Voucher.objects.filter(user=user, used_at__isnull=True, expires_at__gt=timezone.now())


def _reward_open(user, reward: Reward) -> None:
    if reward.countries and country_code(user) not in reward.countries:
        raise errors.RewardNotHere()
    level = profile_of(user).level
    if LEVEL_ORDER.index(level) < LEVEL_ORDER.index(reward.min_level):
        raise errors.RewardLocked(details={"level": Level(reward.min_level).label})
    if reward.stock is not None and reward.stock <= 0:
        raise errors.RewardSoldOut()


def catalogue(user):
    found = Reward.objects.filter(is_active=True).select_related("course")
    code = country_code(user) if user is not None else ""
    return [r for r in found if not r.countries or not code or code in r.countries]


@transaction.atomic
def redeem(user, reward_id) -> dict:
    """Points spent, then the voucher (or the course opened). Returns what was given."""
    require_games(user)
    reward = Reward.objects.select_for_update().filter(pk=reward_id, is_active=True).first()
    if reward is None:
        raise errors.RewardNotFound()
    _reward_open(user, reward)
    if reward.kind != Reward.Kind.COURSE and not can_purchase(user):
        raise errors.CannotBuy()
    course = reward.course if reward.kind == Reward.Kind.COURSE else None
    if reward.kind == Reward.Kind.COURSE and (course is None or course.pro_id is not None):
        raise errors.RewardNotFound()
    spent = points.spend(
        user,
        reward.cost_points,
        key=f"reward:{reward.pk}:{user.pk}:{timezone.now().timestamp()}",
        source_type="reward",
        source_id=reward.pk,
        note=reward.title,
    )
    voucher = enrollment = None
    if course is not None:
        from apps.academy.services import enrollments

        enrollment = enrollments.give(user, course)
    else:
        voucher = create_voucher(
            user,
            kind=reward.kind,
            origin=Voucher.Origin.REWARD,
            amount_minor=reward.amount_off_minor,
            days=reward.validity_days,
        )
    if reward.stock is not None:
        Reward.objects.filter(pk=reward.pk).update(stock=F("stock") - 1)
    record("glow.reward_redeemed", reward, actor=user, metadata={"points": reward.cost_points})
    return {"entry": spent, "voucher": voucher, "course": course, "enrollment": enrollment}


# --- Vouchers on the France Selection --------------------------------------------------------


def take(user, code: str, *, order_id, total: int, express_premium: int | None) -> tuple:
    """(voucher, discount) for an order being placed, inside its transaction. The order
    keeps at least ``glow.voucher_min_to_pay`` FCFA to pay."""
    voucher = usable(user).select_for_update().filter(code=(code or "").strip().upper()).first()
    if voucher is None:
        raise errors.VoucherNotFound()
    if not can_purchase(user):
        raise errors.CannotBuy()
    if voucher.kind == Voucher.Kind.EXPRESS:
        if not express_premium:
            raise errors.VoucherNotForThis()
        discount = express_premium
    else:
        floor = int(setting("glow.voucher_min_to_pay", 1000))
        discount = min(voucher.amount_off_minor, total - floor)
        if discount <= 0:
            raise errors.VoucherNotForThis()
    voucher.used_at = timezone.now()
    voucher.used_for_type = SELECTION
    voucher.used_for_id = order_id
    voucher.save(update_fields=["used_at", "used_for_type", "used_for_id", "updated_at"])
    return voucher, discount


def give_back(source_type: str, source_id) -> int:
    """The order was not paid or was refunded: its voucher can be used again (if valid)."""
    return Voucher.objects.filter(used_for_type=source_type, used_for_id=source_id).update(
        used_at=None, used_for_type="", used_for_id=None, updated_at=timezone.now()
    )
