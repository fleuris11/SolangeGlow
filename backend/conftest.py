import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _run_on_commit_now(monkeypatch):
    """Tests run inside a transaction that is never committed: run the "after commit"
    callbacks (Celery tasks, notifications) at once, as production does after commit."""

    def immediate(func, using=None, robust=False):
        func()

    monkeypatch.setattr("django.db.transaction.on_commit", immediate)


@pytest.fixture(autouse=True)
def _reset_console_outbox():
    from apps.core.providers.console import OUTBOX

    OUTBOX.clear()
    yield
    OUTBOX.clear()


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture(autouse=True)
def _no_real_livekit(settings):
    """Never a real LiveKit in the tests: off unless a test takes `fake_livekit`."""
    settings.LIVEKIT_URL = ""
    settings.LIVEKIT_API_KEY = ""
    settings.LIVEKIT_API_SECRET = ""


@pytest.fixture
def fake_livekit():
    from apps.core.providers import livekit

    fake = livekit.FakeLiveKit()
    livekit.use_fake(fake)
    yield fake
    livekit.use_fake(None)
