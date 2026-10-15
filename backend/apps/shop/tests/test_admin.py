"""Back office: the review queue (accept, refuse with a reason, unblock) and read-only orders."""

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.shop.models import Product

from .factories import order, product

pytestmark = pytest.mark.django_db


@pytest.fixture
def team(client):
    admin = UserFactory(is_staff=True, is_superuser=True)
    client.force_login(admin)
    return client


def test_lists_open(team):
    placed = order()
    for name in (
        "shop_product",
        "shop_order",
        "shop_forbiddenterm",
        "shop_category",
        "shop_promocode",
        "shop_flashsale",
        "shop_bundle",
        "shop_shopprofile",
    ):
        assert team.get(reverse(f"admin:{name}_changelist")).status_code == 200
    assert team.get(reverse("admin:shop_order_change", args=[placed.pk])).status_code == 200
    item = placed.lines.get().product
    assert team.get(reverse("admin:shop_product_change", args=[item.pk])).status_code == 200
    queue = reverse("admin:shop_product_changelist") + "?status__exact=in_review"
    assert team.get(queue).status_code == 200


def test_accept_refuse_unblock_in_one_click(team):
    item = product(title="Lait éclaircissant")
    assert item.status == Product.Status.IN_REVIEW
    team.get(reverse("admin:shop_product_approve_detail", args=[item.pk]))
    item.refresh_from_db()
    assert item.status == Product.Status.PUBLISHED
    team.get(
        reverse("admin:shop_product_approve_detail", args=[item.pk])
    )  # twice: an error message
    page = team.get(reverse("admin:shop_product_refuse_detail", args=[item.pk]))
    assert page.status_code == 200
    team.post(reverse("admin:shop_product_refuse_detail", args=[item.pk]), {"reason": "Interdit"})
    item.refresh_from_db()
    assert item.status == Product.Status.BLOCKED and item.review_reason == "Interdit"
    team.get(reverse("admin:shop_product_unblock_detail", args=[item.pk]))
    item.refresh_from_db()
    assert item.status == Product.Status.DRAFT


def test_the_review_group_exists():
    group = Group.objects.get(name="Shop review")
    assert group.permissions.filter(codename="review_product").exists()
