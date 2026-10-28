"""Demo gifts (seed_demo): Grâce, in Paris, offers a service at Aïcha's to Fifamè, a Glow gift
card of 30 € to Awa, and a gift for Mother's day sent in three weeks."""

from __future__ import annotations

import datetime

from django.utils import timezone

from apps.accounts.models import User
from apps.payments import services as payment_services
from apps.pros.models import Service

from . import services
from .models import Gift, Occasion


def _paid(gift: Gift) -> None:
    payment = gift.payment
    payment_services.mark_paid(
        payment, amount_minor=payment.total_minor, currency="EUR", key=f"demo:{payment.pk}"
    )


def seed_gifts() -> dict:
    grace = User.objects.filter(phone="+33612340204").first()
    if grace is None or Gift.objects.filter(giver=grace).exists():
        return {"gifts": 0}
    service = (
        Service.objects.filter(
            pro__user__phone="+2290197000101",
            is_active=True,
            archived_at__isnull=True,
            price_kind=Service.PriceKind.FIXED,
            price_minor__isnull=False,
            currency="XOF",
        )
        .order_by("price_minor")
        .first()
    )
    made = []
    if service is not None:
        made.append(
            services.offer(
                grace,
                services.quote(Gift.Kind.SERVICE, service_id=service.pk),
                recipient_name="Fifamè",
                recipient_phone="+2290196000202",
                occasion=Occasion.BIRTHDAY,
                message="Joyeux anniversaire ma sœur ! Fais-toi belle.",
            )
        )
    made.append(
        services.offer(
            grace,
            services.quote(Gift.Kind.CARD, amount_minor=3_000),
            recipient_name="Awa",
            recipient_phone="+2290197000201",
            occasion=Occasion.YEAR_END,
            message="Bonnes fêtes ! Fais-toi plaisir.",
        )
    )
    if service is not None:
        made.append(
            services.offer(
                grace,
                services.quote(Gift.Kind.SERVICE, service_id=service.pk),
                recipient_name="Maman Pélagie",
                recipient_phone="+2290197000777",
                occasion=Occasion.MOTHERS_DAY,
                message="Bonne fête maman, je t'aime.",
                send_at=timezone.now() + datetime.timedelta(days=21),
            )
        )
    for gift in made:
        _paid(gift)
    return {"gifts": len(made)}
