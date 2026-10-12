import pytest

from apps.social import eligibility

from .factories import FakeBookings


@pytest.fixture
def bookings():
    """A fake booking module that registers its finished bookings for reviews."""
    fake = FakeBookings()
    eligibility.register(fake)
    yield fake
    eligibility.unregister("booking")
