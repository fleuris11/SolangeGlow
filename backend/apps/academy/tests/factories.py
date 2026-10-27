"""Courses, lessons and students for the academy tests."""

from __future__ import annotations

from django.utils import timezone

from apps.core.media.models import MediaAsset
from apps.core.tests.factories import PlatformSettingFactory
from apps.messaging.tests.factories import adult
from apps.payments import services as payments
from apps.payments.models import Payment
from apps.pros.tests.factories import ProFactory

from ..models import Course, Lesson, Module, Question


def trainer(name="Prisca", **kwargs):
    return ProFactory(business_name=f"Institut {name}", user=adult(name), **kwargs)


def video(owner, seconds=240, status=MediaAsset.Status.READY) -> MediaAsset:
    return MediaAsset.objects.create(
        owner=owner,
        kind="video",
        purpose="lesson_video",
        visibility="private",
        status=status,
        duration_seconds=seconds,
        variants={
            "low": {"path": "video/x/low.mp4"},
            "medium": {"path": "video/x/medium.mp4"},
            "poster_medium": {"path": "video/x/p.webp"},
        }
        if status == MediaAsset.Status.READY
        else {},
    )


def course(
    pro=None,
    *,
    pricing=Course.Pricing.FREE,
    price=0,
    status=Course.Status.PUBLISHED,
    modules=(("Les bases", 2),),
    quiz=0,
    badge=False,
    country=None,
    author=None,
) -> Course:
    """A course with modules of n lessons (and quiz questions per module)."""
    country = country or (pro.country if pro else None)
    if country is None:
        from apps.core.tests.factories import CountryFactory

        country = CountryFactory()
    author = author or (pro.user if pro else adult("Équipe"))
    created = Course.objects.create(
        slug=f"cours-{Course.objects.count() + 1}",
        pro=pro,
        author=author,
        country=country,
        title="Maquillage mariée",
        currency="XOF",
        pricing=pricing,
        price_minor=price,
        status=status,
        published_at=timezone.now() if status == Course.Status.PUBLISHED else None,
        counts_for_badge=badge,
    )
    for index, (title, lessons) in enumerate(modules):
        module = Module.objects.create(course=created, title=title, position=index)
        for position in range(lessons):
            Lesson.objects.create(
                module=module,
                title=f"Leçon {index + 1}.{position + 1}",
                video=video(author),
                duration_seconds=240,
                position=position,
                is_preview=index == 0 and position == 0,
            )
        for position in range(quiz):
            Question.objects.create(
                module=module,
                text=f"Question {position + 1}",
                choices=["Oui", "Non"],
                correct=0,
                position=position,
            )
    return created


def pay(payment: Payment) -> Payment:
    payments.mark_paid(
        payment, amount_minor=payment.total_minor, currency=payment.currency, key=str(payment.pk)
    )
    return Payment.objects.get(pk=payment.pk)


def setting(key, value, value_type="integer", country=None):
    return PlatformSettingFactory(key=key, value=str(value), value_type=value_type, country=country)
