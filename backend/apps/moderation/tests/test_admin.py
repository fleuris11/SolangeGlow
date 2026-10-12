import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.moderation import services
from apps.moderation.models import ModerationCase, Sanction
from apps.social.models import Visibility
from apps.social.tests.factories import person, published_post

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client):
    client.force_login(User.objects.create_superuser(email="team@example.com", password="pass-123"))
    return client


@pytest.fixture
def case():
    post = published_post(person(name="Troll"), caption="Contenu douteux")
    services.report(person(name="Awa"), post, reason="harassment")
    return ModerationCase.objects.get()


def test_queue_and_detail_render(admin_client, case):
    queue = admin_client.get(reverse("admin:moderation_moderationcase_changelist"))
    assert queue.status_code == 200 and "Contenu douteux" in queue.content.decode()
    detail = admin_client.get(reverse("admin:moderation_moderationcase_change", args=[case.pk]))
    assert detail.status_code == 200


def test_one_click_remove_and_sanction(admin_client, case):
    url = reverse("admin:moderation_moderationcase_remove_and_sanction_row", args=[case.pk])
    response = admin_client.get(url)
    assert response.status_code == 302
    case.refresh_from_db()
    assert case.status == "removed"
    assert case.target.visibility == Visibility.REMOVED
    assert Sanction.objects.get().level == "warning"


def test_one_click_keep(admin_client, case):
    admin_client.get(reverse("admin:moderation_moderationcase_keep_row", args=[case.pk]))
    case.refresh_from_db()
    assert case.status == "kept"


@pytest.mark.parametrize(
    "name",
    [
        "admin:social_post_changelist",
        "admin:social_comment_changelist",
        "admin:social_story_changelist",
        "admin:social_review_changelist",
        "admin:moderation_sanction_changelist",
        "admin:moderation_report_changelist",
    ],
)
def test_social_admin_pages(admin_client, case, name):
    assert admin_client.get(reverse(name)).status_code == 200
