import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.accounts.models import User
from apps.core.audit.models import AuditEvent
from apps.pros import services
from apps.pros.apps import VERIFICATION_GROUP
from apps.pros.models import ProProfile, ProVerification

from .factories import ProFactory, add_service, picture

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner():
    return User.objects.create_superuser(email="owner@example.com", password="s3cret-pass")


@pytest.fixture
def admin_client(client, owner):
    client.force_login(owner)
    return client


@pytest.fixture
def verification():
    pro = ProFactory(slug="aicha")
    return services.submit_verification(
        pro, document=picture("id.jpg", fmt="JPEG"), selfie=picture(), document_type="id_card"
    )


@pytest.mark.parametrize(
    "query",
    ["", "?status=published", "?verification_status=pending", "?q=Cotonou", "?kind=business"],
)
def test_pro_list_and_filters(admin_client, query):
    pro = ProFactory()
    add_service(pro)
    response = admin_client.get(reverse("admin:pros_proprofile_changelist") + query)
    assert response.status_code == 200


def test_pro_change_page_and_map(admin_client):
    pro = ProFactory()
    assert (
        admin_client.get(reverse("admin:pros_proprofile_change", args=[pro.pk])).status_code == 200
    )
    response = admin_client.get(reverse("admin:pros_proprofile_map"))
    assert response.status_code == 200
    assert pro.display_name in response.content.decode()


def test_suspend_from_the_list(admin_client, owner):
    pro = ProFactory()
    url = reverse("admin:pros_proprofile_changelist")
    admin_client.post(url, {"action": "suspend_selected", "_selected_action": [pro.pk]})
    pro.refresh_from_db()
    assert pro.status == ProProfile.Status.SUSPENDED
    assert AuditEvent.objects.filter(action="pros.suspended", actor=owner).exists()
    admin_client.post(url, {"action": "reinstate_selected", "_selected_action": [pro.pk]})
    pro.refresh_from_db()
    assert pro.status == ProProfile.Status.PUBLISHED


def test_verification_group_exists_with_its_permission():
    group = Group.objects.get(name=VERIFICATION_GROUP)
    assert group.permissions.filter(codename="review_identity").exists()


def test_staff_without_the_role_never_sees_identity_documents(client, verification):
    staff = User.objects.create_user(email="mod@example.com", password="pass-12345", is_staff=True)
    client.force_login(staff)
    assert client.get(reverse("admin:pros_proverification_changelist")).status_code == 403
    url = reverse("admin:pros_proverification_file", args=[verification.pk, "document"])
    assert client.get(url).status_code == 403
    assert not AuditEvent.objects.filter(action="pros.identity_viewed").exists()


def test_verification_team_reviews_and_every_view_is_journaled(client, verification):
    reviewer = User.objects.create_user(
        email="verif@example.com", password="pass-12345", is_staff=True
    )
    reviewer.groups.add(Group.objects.get(name=VERIFICATION_GROUP))
    client.force_login(reviewer)

    queue = client.get(reverse("admin:pros_proverification_changelist"))
    assert queue.status_code == 200
    change_url = reverse("admin:pros_proverification_change", args=[verification.pk])
    assert client.get(change_url).status_code == 200

    image = client.get(reverse("admin:pros_proverification_file", args=[verification.pk, "selfie"]))
    assert image.status_code == 200 and image["Content-Type"] == "image/jpeg"
    assert "no-store" in image["Cache-Control"]
    assert AuditEvent.objects.filter(action="pros.identity_viewed", actor=reviewer).exists()

    client.post(change_url, {"rejection_reason": "", "pros_proverification_approve": "1"})
    verification.refresh_from_db()
    assert verification.status == ProVerification.Status.APPROVED
    assert verification.pro.is_verified
