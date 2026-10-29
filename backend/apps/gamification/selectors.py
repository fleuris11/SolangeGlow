"""What the screens of the games show (payloads read by the serializers)."""

from __future__ import annotations

import datetime

from django.utils import timezone

from apps.core.media.services import asset_payload
from apps.pros.models import Trade
from apps.social.serializers import author_payload

from .models import LEVEL_ORDER, Action, Poll, Reward, Voucher
from .services import (
    celebrations,
    challenges,
    points,
    polls,
    quiz,
    referrals,
    rewards,
    streaks,
    wheel,
)
from .services.common import country_code, games_on, profile_of, setting, today


def _media(asset):
    return asset_payload(asset) if asset is not None and asset.is_ready else None


def me(user) -> dict:
    profile = profile_of(user)
    scale, caps = points.scale(), points.caps()
    uncapped = points.uncapped()
    day = today(user)
    done = points.earned_on(user, day)
    actions = [a for a in Action.values if a not in (Action.REWARD, Action.ADJUSTMENT)]
    return {
        **points.summary(user),
        "streak": streaks.state(user),
        "referral": {
            "code": profile.referral_code,
            "path": referrals.link_path(profile),
            **referrals.stats(user),
            "referrer_points": int(scale.get(Action.REFERRAL, 0)),
            "referee_points": int(scale.get(Action.REFERRED, 0)),
        },
        "scale": [
            {
                "action": action,
                "points": int(scale.get(action, 0) or 0),
                "per_day": caps.get(action),
                "bonus": action in uncapped,
            }
            for action in actions
            if int(scale.get(action, 0) or 0) > 0
        ],
        "daily_max": int(setting("glow.daily_max_points", 400)),
        "earned_today": done["ceiling"],
        "games_open": games_on(user),
        "wheel_open": wheel.wheel_on(user),
    }


def history(user) -> list[dict]:
    return [
        {
            "id": entry.pk,
            "amount": entry.amount,
            "action": entry.action,
            "note": entry.note,
            "created_at": entry.created_at,
        }
        for entry in points.history(user, int(setting("glow.history_size", 100)))
    ]


def voucher_payload(voucher: Voucher) -> dict:
    return {
        "id": voucher.pk,
        "code": voucher.code,
        "kind": voucher.kind,
        "origin": voucher.origin,
        "label": voucher.label,
        "amount_off_minor": voucher.amount_off_minor,
        "currency": voucher.currency,
        "expires_at": voucher.expires_at,
        "used_at": voucher.used_at,
    }


def vouchers(user) -> list[dict]:
    recent = timezone.now() - datetime.timedelta(days=30)
    rows = Voucher.objects.filter(user=user, expires_at__gt=recent).order_by(
        "used_at", "expires_at"
    )
    return [voucher_payload(v) for v in rows[:50]]


def rewards_payload(user) -> list[dict]:
    left = points.balance(user)
    level = LEVEL_ORDER.index(profile_of(user).level)
    return [
        {
            "id": reward.pk,
            "title": reward.title,
            "description": reward.description,
            "kind": reward.kind,
            "cost_points": reward.cost_points,
            "amount_off_minor": reward.amount_off_minor,
            "course": {"slug": reward.course.slug, "title": reward.course.title}
            if reward.kind == Reward.Kind.COURSE and reward.course
            else None,
            "min_level": reward.min_level,
            "locked": LEVEL_ORDER.index(reward.min_level) > level,
            "sold_out": reward.stock is not None and reward.stock <= 0,
            "affordable": reward.cost_points <= left,
        }
        for reward in rewards.catalogue(user)
    ]


# --- Quiz ------------------------------------------------------------------------------------


def quiz_payload(user) -> dict | None:
    day = today(user) if user else timezone.localdate()
    found = quiz.of_day(day)
    if found is None:
        return None
    mine = quiz.answers_of(user, found)
    questions = []
    for question in found.questions.all():
        answered = mine.get(question.pk)
        questions.append(
            {
                "id": question.pk,
                "position": question.position,
                "text": question.text,
                "choices": question.choices(),
                "image": _media(question.image),
                "audio": _media(question.audio),
                "answered": answered.choice if answered else None,
                "correct": answered.is_correct if answered else None,
                "answer": question.answer if answered else None,
                "explanation": question.explanation if answered else "",
            }
        )
    return {
        "date": found.date,
        "questions": questions,
        "points_per_answer": int(points.scale().get(Action.QUIZ, 0)),
        "score": sum(1 for q in questions if q["correct"]),
        "answered": sum(1 for q in questions if q["answered"] is not None),
    }


# --- Wheel -----------------------------------------------------------------------------------


def spin_payload(spin) -> dict | None:
    if spin is None:
        return None
    return {
        "prize_id": spin.prize_id,
        "label": spin.label,
        "kind": spin.kind,
        "points": spin.points,
        "voucher": voucher_payload(spin.voucher) if spin.voucher_id else None,
    }


def wheel_payload(user) -> dict:
    found = wheel.state(user)
    return {
        "open": found["open"],
        "can_spin": found["can_spin"],
        "prizes": [
            {
                "id": row["prize"].pk,
                "label": row["prize"].label,
                "kind": row["prize"].kind,
                "chance": row["chance"],
            }
            for row in found["prizes"]
        ],
        "today": spin_payload(found["today"]),
    }


# --- « Help me choose » ----------------------------------------------------------------------


def poll_payload(poll: Poll, viewer) -> dict:
    mine = viewer is not None and poll.author_id == viewer.pk
    voted = polls.my_vote(viewer, poll)
    ended = poll.ends_at <= timezone.now()
    return {
        "id": poll.pk,
        "caption": poll.caption,
        "author": author_payload(poll.author),
        "photo_a": _media(poll.photo_a),
        "photo_b": _media(poll.photo_b),
        "label_a": poll.label_a,
        "label_b": poll.label_b,
        "ends_at": poll.ends_at,
        "ended": ended,
        "mine": mine,
        "my_vote": voted,
        # The result is shown once she voted, to the author, or when the vote is over.
        "result": polls.result(poll) if (voted or mine or ended) else None,
    }


# --- Photo challenge -------------------------------------------------------------------------


def entry_payload(entry, viewer, voted: set) -> dict:
    return {
        "id": entry.pk,
        "author": author_payload(entry.author),
        "photo": _media(entry.photo),
        "caption": entry.caption,
        "votes": entry.votes,
        "voted": entry.pk in voted,
        "mine": viewer is not None and entry.author_id == viewer.pk,
    }


def featured_payload(day=None) -> dict | None:
    found = challenges.featured(day)
    if found is None:
        return None
    return {
        "theme": found.theme,
        "ends_on": found.ends_on,
        "winner": entry_payload(found.winner, None, set()),
    }


def challenge_payload(viewer) -> dict:
    day = today(viewer) if viewer else timezone.localdate()
    found = challenges.current(day)
    current = None
    if found is not None:
        voted = challenges.voted_ids(viewer, found)
        rows = list(challenges.entries(found, viewer)[:100])
        mine = next((e for e in rows if viewer and e.author_id == viewer.pk), None)
        current = {
            "id": found.pk,
            "theme": found.theme,
            "description": found.description,
            "starts_on": found.starts_on,
            "ends_on": found.ends_on,
            "entries": [entry_payload(e, viewer, voted) for e in rows],
            "my_entry": mine.pk if mine else None,
            "votes_left": challenges.votes_left(viewer, found) if viewer else 0,
        }
    return {"current": current, "featured": featured_payload(day)}


# --- Rankings --------------------------------------------------------------------------------


def rankings_payload(*, month=None, city: str = "", trade_key: str = "") -> dict:
    from .services import rankings

    month = month or rankings.latest_month()
    if month is None:
        return {"month": None, "cities": [], "trades": [], "city": "", "trade": "", "rows": []}
    found = rankings.choices(month)
    trades = list(Trade.objects.filter(pk__in=found["trades"]).order_by("position"))
    city = next((c for c in found["cities"] if c.lower() == city.lower()), "") or (
        found["cities"][0] if found["cities"] else ""
    )
    trade = next((t for t in trades if t.key == trade_key), None) or (trades[0] if trades else None)
    rows = rankings.table(month=month, city=city, trade_id=trade.pk) if trade else []
    return {
        "month": month,
        "cities": found["cities"],
        "trades": [{"key": t.key, "name": t.name, "icon": t.icon} for t in trades],
        "city": city,
        "trade": trade.key if trade else "",
        "rows": [
            {
                "position": row.position,
                "slug": row.pro.slug,
                "name": row.pro.display_name,
                "photo": _media(row.pro.photo),
                "level": row.pro.level,
                "verified": row.pro.is_verified,
                "average": row.average,
                "reviews": row.reviews,
            }
            for row in rows
        ],
    }


# --- Calendar --------------------------------------------------------------------------------


def celebrations_payload(user, country: str = "", *, limit: int | None = None) -> list[dict]:
    code = country or (country_code(user) if user else "") or "BJ"
    day = timezone.localdate()
    return [
        {
            "id": c.pk,
            "name": c.name,
            "message": c.message,
            "date": when,
            "days_left": (when - day).days,
            "trade": c.trade.key if c.trade_id else "",
            "search": c.search,
            "gift_occasion": c.gift_occasion,
        }
        for c, when in celebrations.upcoming(code, day, limit=limit)
    ]


# --- Home page -------------------------------------------------------------------------------


def today_payload(viewer) -> dict:
    signed = viewer is not None
    open_ = games_on(viewer) if signed else True
    found_quiz = quiz_payload(viewer) if signed else None
    current = challenges.current(today(viewer) if signed else None)
    to_vote = polls.to_vote(viewer).first() if signed else None
    upcoming = celebrations_payload(viewer, limit=1) if signed else []
    payload = {
        "signed_in": signed,
        "games_open": open_,
        "summary": None,
        "streak": None,
        "quiz": None,
        "wheel": None,
        "challenge": {
            "theme": current.theme,
            "ends_on": current.ends_on,
            "entries": current.entries.filter(visibility="visible").count(),
        }
        if current
        else None,
        "featured": featured_payload(),
        "poll": poll_payload(to_vote, viewer) if to_vote else None,
        "celebration": upcoming[0] if upcoming else None,
    }
    if signed and open_:
        found = wheel.state(viewer)
        payload.update(
            summary=points.summary(viewer),
            streak=streaks.state(viewer),
            quiz={
                "total": len(found_quiz["questions"]),
                "answered": found_quiz["answered"],
                "score": found_quiz["score"],
            }
            if found_quiz
            else None,
            wheel={"open": found["open"], "can_spin": found["can_spin"]},
        )
    return payload
