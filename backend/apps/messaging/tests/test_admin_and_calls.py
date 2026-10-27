import pytest
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.core.audit.models import AuditEvent
from apps.messaging import services
from apps.messaging.models import Conversation

from .factories import adult, pro

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client):
    admin = UserFactory(is_staff=True, is_superuser=True, email="admin@example.com")
    client.force_login(admin)
    return client


def test_the_team_only_sees_reported_conversations_and_disputes(admin_client):
    awa, aicha = adult("Awa"), pro("Aïcha Tresses")
    private = services.start_direct(adult("Zoé"), pro("Gloria Nails"))
    services.send(private.members.first().user, private.pk, text="Secret")
    reported = services.start_direct(awa, aicha)
    message = services.send(aicha, reported.pk, text="Paie-moi par Western Union")
    services.report_message(awa, message.pk, reason="scam")
    dispute = services.create_group(
        None, [awa, aicha], title="Litige 42", purpose=Conversation.Purpose.DISPUTE
    )

    listing = admin_client.get(reverse("admin:messaging_conversation_changelist"))
    shown = {str(c.pk) for c in listing.context["cl"].result_list}
    assert shown == {str(reported.pk), str(dispute.pk)}

    hidden = admin_client.get(reverse("admin:messaging_conversation_change", args=[private.pk]))
    assert hidden.status_code == 302  # not found for the admin: back to the list

    page = admin_client.get(reverse("admin:messaging_conversation_change", args=[reported.pk]))
    assert page.status_code == 200 and "Western Union" in page.content.decode()
    event = AuditEvent.objects.get(action="messaging.conversation_viewed")
    assert event.target_id == str(reported.pk) and event.metadata == {"reason": "report"}

    # The moderation queue opens the conversation at the reported message.
    jump = admin_client.get(reverse("admin:messaging_message_change", args=[message.pk]))
    assert jump.status_code == 302 and str(reported.pk) in jump["Location"]
