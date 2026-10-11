import datetime
import io

import factory
from django.contrib.gis.geos import Point
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

from apps.accounts.tests.factories import UserFactory
from apps.core.tests.factories import CountryFactory
from apps.pros.models import OpeningPeriod, ProProfile, Service, ServiceStep, Trade

COTONOU = Point(2.4183, 6.3654, srid=4326)  # (longitude, latitude)


def trade(key: str) -> Trade:
    """Trades come from a data migration: they exist in every test database."""
    return Trade.objects.get(key=key)


class ProFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProProfile
        skip_postgeneration_save = True

    user = factory.SubFactory(UserFactory, phone=factory.Sequence(lambda n: f"+22901970{n:05d}"))
    business_name = factory.Sequence(lambda n: f"Salon {n}")
    slug = factory.Sequence(lambda n: f"salon-{n}")
    country = factory.SubFactory(CountryFactory)
    currency = "XOF"
    city = "Cotonou"
    district = "Fidjrossè"
    location = COTONOU
    status = ProProfile.Status.PUBLISHED
    published_at = factory.LazyFunction(timezone.now)

    @factory.post_generation
    def trades(self, create, extracted, **kwargs):
        if create:
            self.trades.set([trade(key) for key in (extracted or ["braids"])])


def add_service(pro, *, name="Knotless braids", price=15000, minutes=180, kind="fixed"):
    service = Service.objects.create(
        pro=pro,
        name=name,
        price_kind=kind,
        price_minor=None if kind == "quote" else price,
        currency=pro.currency,
        duration_minutes=minutes,
    )
    ServiceStep.objects.create(service=service, duration_minutes=minutes)
    return service


def open_every_day(pro, opens=datetime.time(0, 0), closes=datetime.time(23, 59)):
    for weekday in range(7):
        OpeningPeriod.objects.create(pro=pro, weekday=weekday, opens_at=opens, closes_at=closes)


def picture(name="photo.png", size=(320, 240), fmt="PNG") -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", size, (200, 16, 46)).save(buffer, fmt)
    content_type = "image/png" if fmt == "PNG" else "image/jpeg"
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)
