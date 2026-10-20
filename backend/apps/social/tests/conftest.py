import pytest

from apps.social import eligibility

from .factories import FakeBookings


@pytest.fixture
def bookings():
    """A fake booking module that registers its finished bookings for reviews.

    The real one (apps.booking) is put back afterwards.
    """
    real = eligibility.provider_for("booking")
    fake = FakeBookings()
    eligibility.register(fake)
    yield fake
    eligibility.unregister("booking")
    if real is not None:
        eligibility.register(real)
