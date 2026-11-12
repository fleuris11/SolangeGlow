"""Every list and every « add » screen of the back-office opens for the owner: no error page."""

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.urls import NoReverseMatch, reverse

pytestmark = pytest.mark.django_db


def test_every_admin_list_and_add_page_opens(client):
    owner = get_user_model().objects.create_superuser(
        email="owner@example.com", password="s3c-ret1"
    )
    client.force_login(owner)
    broken = []
    opened = 0
    for model in admin.site._registry:
        meta = model._meta
        for kind in ("changelist", "add"):
            try:
                url = reverse(f"admin:{meta.app_label}_{meta.model_name}_{kind}")
            except NoReverseMatch:
                continue
            response = client.get(url)
            opened += 1
            # 403: a screen where nothing is added by hand (read-only journals).
            if response.status_code not in (200, 302, 403):
                broken.append((url, response.status_code))
    assert broken == []
    assert opened > 100
    assert client.get(reverse("admin:index")).status_code == 200
