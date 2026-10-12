import datetime

from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.core.media.models import MediaAsset
from apps.core.tests.factories import CountryFactory
from apps.pros.hours import zone_of
from apps.pros.models import OpeningPeriod
from apps.pros.tests.factories import ProFactory
from apps.social.models import Follow


def adult(name="Awa", **kwargs):
    kwargs.setdefault("country", CountryFactory())
    kwargs.setdefault("birth_date", datetime.date(1995, 4, 12))
    return UserFactory(first_name=name, **kwargs)


def minor(name="Lina", **kwargs):
    return adult(name, birth_date=timezone.localdate().replace(year=timezone.localdate().year - 15))


def pro(name="Aïcha Tresses", **kwargs):
    profile = ProFactory(business_name=name, user=adult(name.split()[0]), **kwargs)
    return profile.user


def follow(follower, followed):
    Follow.objects.get_or_create(follower=follower, followed=followed)


def closed_today(user):
    """Opening hours that exclude today (in her time zone): she is away now."""
    profile = user.pro_profile
    today = timezone.now().astimezone(zone_of(profile)).weekday()
    OpeningPeriod.objects.create(
        pro=profile,
        weekday=(today + 3) % 7,
        opens_at=datetime.time(9, 0),
        closes_at=datetime.time(18, 0),
    )


def upload(owner, purpose="message_photo", kind="image", status=MediaAsset.Status.READY):
    return MediaAsset.objects.create(
        owner=owner,
        kind=kind,
        purpose=purpose,
        visibility="private",
        status=status,
        variants={"medium": {"path": "image/x/medium.webp"}}
        if kind == "image"
        else {"voice": {"path": "audio/x/voice.webm"}},
    )
