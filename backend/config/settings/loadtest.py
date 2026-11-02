"""The production image with the test payment provider: load tests only (loadtest/)."""

from .prod import *  # noqa: F403

PAYMENTS_FAKE_ENABLED = True
BACKOFFICE_REQUIRE_2FA = False
