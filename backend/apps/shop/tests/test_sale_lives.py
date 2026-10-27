"""Sales lives: a verified shop plans and goes on air, pins products, viewers watch without
an account and buy without leaving; each paid order counts in the live; the replay stays
public a few days."""

import datetime

import pytest
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.live import errors as live_errors
from apps.live import services as live
from apps.live.models import LiveRoom
from apps.notifications.models import Notification
from apps.pros.models import ProProfile
from apps.shop import errors
from apps.shop.models import Order, SaleLive
from apps.shop.services import cart, checkout
from apps.shop.services import lives as sale_lives
from apps.social.models import Follow

from .factories import buyer, choice, pay, product, shop_owner

pytestmark = pytest.mark.django_db
S = "sale"
H = {"HTTP_X_SG_CLIENT": "web"}


def plan(owner, minutes=5, **values):
    values.setdefault("title", "Nouveautés gloss")
    values.setdefault("duration_minutes", 60)
    return sale_lives.plan(
        owner, starts_at=timezone.now() + datetime.timedelta(minutes=minutes), **values
    )


def test_only_a_verified_shop_plans_a_live():
    owner = shop_owner()
    with pytest.raises(errors.InvalidSaleLive):
        plan(owner, minutes=-5)
    with pytest.raises(errors.InvalidSaleLive):
        plan(owner, duration_minutes=500)
    ProProfile.objects.filter(user=owner).update(
        verification_status=ProProfile.Verification.PENDING
    )
    owner.refresh_from_db()
    with pytest.raises(errors.VerificationNeeded):
        plan(owner)


def test_free_lives_count_training_and_sales_together():
    owner = shop_owner()
    plan(owner)
    plan(owner, minutes=120)
    with pytest.raises(live_errors.MonthlyLimit):
        plan(owner, minutes=240)
    quota = APIClient()
    quota.force_authenticate(owner)
    assert quota.get(reverse("v1:live-quota")).json() == {"used": 2, "allowed": 2}


def test_viewers_watch_without_an_account_and_buy_from_the_live(fake_livekit):
    owner = shop_owner()
    gloss = product(owner, title="Gloss Mangue", price=4_000)
    fan = buyer("Bintou")
    Follow.objects.create(follower=fan, followed=owner)
    sale = plan(owner)

    sale_lives.pin(owner, sale.pk, gloss.pk)
    live.start(owner, S, sale.pk)
    sale.refresh_from_db()
    assert sale.status == SaleLive.Status.LIVE
    assert Notification.objects.filter(user=fan, event_key="shop.live_on_air").exists()

    guest = live.join(AnonymousUser(), S, sale.pk)
    assert guest["identity"].startswith("guest-") and not guest["host"]
    seen = live.state(AnonymousUser(), S, sale.pk)
    assert seen["sale"]["pins"][0]["name"] == "Gloss Mangue" and seen["sale"]["pins"][0]["pinned"]
    assert seen["sale"]["revenue_minor"] is None and not seen["can_ask"]
    with pytest.raises(live_errors.SignInToAsk):
        live.ask(AnonymousUser(), S, sale.pk, "Dispo en rouge ?")
    with pytest.raises(live_errors.HandsClosed):
        live.raise_hand(fan, S, sale.pk)
    live.ask(fan, S, sale.pk, "Il tient combien de temps ?")

    client = buyer("Awa")
    cart.add(client, variant_id=gloss.variants.first().pk, sale_live_id=sale.pk)
    group, orders = checkout.place_orders(client, [choice(owner)])
    assert orders[0].sale_live_id == sale.pk
    sent_before = len(fake_livekit.sent("SendData"))
    pay(group)
    sale.refresh_from_db()
    assert sale.orders_count == 1 and sale.revenue_minor == 4_000
    purchase = fake_livekit.sent("SendData")[sent_before:]
    assert purchase  # « somebody just bought Gloss Mangue »
    order = Order.objects.get(pk=orders[0].pk)
    assert order.counted_in_live
    from apps.shop.services.lives import count_purchase

    count_purchase(order)  # counted once
    sale.refresh_from_db()
    assert sale.orders_count == 1
    host = live.state(owner, S, sale.pk)
    assert host["sale"]["revenue_minor"] == 4_000 and host["sale"]["orders_count"] == 1

    sale_lives.unpin(owner, sale.pk, gloss.pk)
    assert not live.state(fan, S, sale.pk)["sale"]["pins"][0]["pinned"]
    with pytest.raises(errors.SaleLiveNotFound):
        sale_lives.cancel(owner, sale.pk)  # on air: it cannot be cancelled any more


def test_a_line_from_another_shop_does_not_count():
    owner, other = shop_owner(), shop_owner("Fatou Braids")
    sale = plan(owner)
    SaleLive.objects.filter(pk=sale.pk).update(status=SaleLive.Status.LIVE)
    item = product(other)
    client = buyer()
    added = cart.add(client, variant_id=item.variants.first().pk, sale_live_id=sale.pk)
    assert added.sale_live_id is None


def test_the_shop_page_shows_its_lives_and_replays(fake_livekit):
    owner = shop_owner()
    product(owner)
    coming = plan(owner, minutes=60 * 24)
    past = plan(owner, minutes=10)
    live.start(owner, S, past.pk)
    live.end_by_host(owner, S, past.pk)
    slug = owner.pro_profile.slug
    page = APIClient().get(reverse("v1:shop-page", args=[slug])).json()
    assert [row["id"] for row in page["lives"]] == [str(coming.pk)]  # no replay yet

    room = LiveRoom.objects.get(kind=S, source_id=past.pk)
    LiveRoom.objects.filter(pk=room.pk).update(
        replay_status=LiveRoom.Replay.READY,
        replay_until=timezone.now() + datetime.timedelta(days=7),
    )
    page = APIClient().get(reverse("v1:shop-page", args=[slug])).json()
    replay = next(row for row in page["lives"] if row["id"] == str(past.pk))
    assert replay["replay"] and replay["link"] == f"/live/sale/{past.pk}"


def test_my_lives_api(fake_livekit):
    owner = shop_owner()
    gloss = product(owner)
    me = APIClient()
    me.force_authenticate(owner)
    url = reverse("v1:my-sale-lives")
    created = me.post(
        url,
        {
            "title": "Nouveautés",
            "starts_at": (timezone.now() + datetime.timedelta(hours=2)).isoformat(),
            "duration_minutes": 45,
        },
        format="json",
        **H,
    ).json()
    assert created["open"] and created["can_sell"] and created["quota"]["used"] == 1
    live_id = created["results"][0]["id"]
    pin_url = reverse("v1:my-sale-live-pin", args=[live_id, gloss.pk])
    assert me.post(pin_url, **H).status_code == 204
    assert me.delete(pin_url, **H).status_code == 204
    state = APIClient().get(reverse("v1:live-state", args=[S, live_id])).json()
    assert state["status"] == "scheduled" and state["sale"]["pins"][0]["pinned"] is False
    cancelled = me.post(reverse("v1:my-sale-live-cancel", args=[live_id]), **H).json()
    assert cancelled["results"] == []
    assert APIClient().get(reverse("v1:live-state", args=[S, live_id])).json()["status"] == (
        "cancelled"
    )
    upcoming = APIClient().get(reverse("v1:live-upcoming"), {"country": "BJ"}).json()
    assert upcoming == []
