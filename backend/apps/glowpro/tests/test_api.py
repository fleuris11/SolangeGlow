"""Glow Pro API: « My plan », trial, payment page, dashboard, widget; admin pages."""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.booking.tests.factories import salon
from apps.messaging.tests.factories import adult

from .factories import premium, priced

pytestmark = pytest.mark.django_db
H = {"HTTP_X_SG_CLIENT": "web"}


def signed_in(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_my_plan_trial_and_payment_page():
    pro = salon()
    priced(pro)
    me = signed_in(pro.user)
    page = me.get(reverse("v1:my-glowpro")).json()
    assert page["current"]["key"] == "free" and page["usage"] == {"staff": 0, "staff_limit": 2}
    premium_plan = next(p for p in page["plans"] if p["key"] == "premium")
    assert premium_plan["price_minor"] == 9_900 and premium_plan["trial_days"] == 30
    trial = me.post(reverse("v1:glowpro-trial"), {"plan": "premium"}, format="json", **H).json()
    assert trial["subscription"]["status"] == "trialing" and trial["current"]["key"] == "premium"
    again = me.post(reverse("v1:glowpro-trial"), {"plan": "premium"}, format="json", **H)
    assert again.status_code == 400 and again.json()["code"] == "already_premium"
    pay = me.post(reverse("v1:glowpro-subscribe"), {"plan": "premium"}, format="json", **H).json()
    assert pay["checkout_url"]
    cancelled = me.post(reverse("v1:glowpro-cancel"), **H).json()
    assert cancelled["subscription"]["cancel_at_period_end"] is True
    assert signed_in(adult()).get(reverse("v1:my-glowpro")).status_code == 404  # not a pro


def test_dashboard_basic_then_complete():
    pro = salon()
    me = signed_in(pro.user)
    basic = me.get(reverse("v1:my-dashboard")).json()
    assert basic["level"] == "basic" and basic["current"] is None and basic["currency"] == "XOF"
    premium(pro)
    complete = me.get(
        reverse("v1:my-dashboard"), {"start": "2030-01-01", "end": "2030-01-31"}
    ).json()
    assert complete["level"] == "complete" and len(complete["current"]["series"]) == 31
    wrong = me.get(reverse("v1:my-dashboard"), {"start": "2030-01-31", "end": "2030-01-01"})
    assert wrong.status_code == 400


def test_widget_settings_and_public_config():
    pro = salon()
    me = signed_in(pro.user)
    refused = me.put(
        reverse("v1:my-widget"),
        {"color": "#7A3E9D", "allowed_domains": ["salon.fr"]},
        format="json",
        **H,
    )
    assert refused.status_code == 403 and refused.json()["code"] == "premium_required"
    premium(pro)
    saved = me.put(
        reverse("v1:my-widget"),
        {"color": "#7A3E9D", "allowed_domains": ["https://salon.fr/rdv"]},
        format="json",
        **H,
    ).json()
    assert saved["allowed_domains"] == ["salon.fr"] and "widget.js" in saved["snippet"]
    public = APIClient().get(reverse("v1:widget", args=[pro.slug])).json()
    assert public == {
        "slug": pro.slug,
        "name": pro.display_name,
        "color": "#7A3E9D",
        "allowed_domains": ["salon.fr"],
    }
    assert APIClient().get(reverse("v1:widget", args=["nobody"])).status_code == 403


def test_admin_pages(client):
    pro = salon()
    premium(pro)
    client.force_login(UserFactory(is_staff=True, is_superuser=True))
    for name in ("plan", "subscription", "widget", "planprice"):
        assert client.get(reverse(f"admin:glowpro_{name}_changelist")).status_code == 200
    subscription = pro.glowpro
    page = reverse("admin:glowpro_subscription_change", args=[subscription.pk])
    assert client.get(page).status_code == 200
    client.get(reverse("admin:glowpro_subscription_end_detail", args=[subscription.pk]))
    subscription.refresh_from_db()
    assert subscription.status == "ended"
