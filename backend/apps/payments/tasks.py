import datetime

from celery import shared_task
from django.utils import timezone


@shared_task(acks_late=True)
def run_deadlines() -> dict:
    """Every 15 minutes: unpaid, unshipped, reminders, automatic release and disputes."""
    from .services.automation import run_all

    return run_all()


@shared_task(acks_late=True)
def run_refund(refund_id: str) -> str:
    from .services.refunds import start_refund

    return start_refund(refund_id).status


@shared_task(acks_late=True)
def run_payout(payout_id: str) -> str:
    from .services.payouts import execute_payout

    return execute_payout(payout_id).status


@shared_task(acks_late=True)
def reconcile_providers() -> list:
    """Once a day: yesterday's statement of each provider that is configured."""
    from .providers import PROVIDERS, ProviderNotConfigured
    from .services.reconciliation import reconcile

    until = timezone.now()
    since = until - datetime.timedelta(days=1)
    runs = []
    for name in PROVIDERS:
        try:
            runs.append(str(reconcile(name, since=since, until=until).pk))
        except ProviderNotConfigured:
            continue
    return runs


@shared_task(acks_late=True)
def send_fake_event(kind: str, reference: str, amount_minor, currency: str) -> int:
    """The test provider answers like a real one: through a signed webhook."""
    from .providers.fake import signed_event
    from .services.webhooks import handle

    body, headers = signed_event(kind, reference, amount_minor, currency)
    return len(handle("fake", headers, body))
