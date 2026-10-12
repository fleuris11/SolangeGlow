import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.moderation import services as moderation
from apps.moderation.models import ModerationCase
from apps.pros.tests.factories import ProFactory, add_service
from apps.social.models import Post

from .factories import asset, person, published_post

pytestmark = pytest.mark.django_db
HEADERS = {"HTTP_X_SG_CLIENT": "web"}


def signed_in(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_feed_for_a_visitor_and_for_a_signed_in_person(api_client):
    author = ProFactory(slug="aicha", business_name="Aïcha Tresses").user
    post = published_post(author, caption="Knotless")
    data = api_client.get(reverse("v1:feed"), {"city": "Cotonou"}).json()
    item = data["results"][0]
    assert item["caption"] == "Knotless" and item["liked"] is False
    assert item["author"]["name"] == "Aïcha Tresses" and item["author"]["pro_slug"] == "aicha"
    assert item["share_url"].endswith(f"/p/{post.pk}")
    assert item["media"][0]["media"]["status"] == "ready"

    fan = person(name="Awa")
    client = signed_in(fan)
    client.post(reverse("v1:post-like", args=[post.pk]), **HEADERS)
    assert client.get(reverse("v1:feed")).json()["results"][0]["liked"] is True


def test_create_a_post_as_a_pro_linked_to_a_service():
    pro = ProFactory()
    service = add_service(pro)
    picture = asset(pro.user)
    response = signed_in(pro.user).post(
        reverse("v1:post-create"),
        {"kind": "photo", "media": [{"id": str(picture.pk)}], "caption": "Nouveau look",
         "service_id": str(service.pk), "trade": "braids"},
        format="json",
        **HEADERS,
    )  # fmt: skip
    assert response.status_code == 201
    data = response.json()
    assert data["service"]["name"] == service.name and data["trade"]["key"] == "braids"
    assert data["is_mine"] is True


def test_draft_is_only_visible_to_its_author():
    author = person()
    draft = (
        signed_in(author)
        .post(
            reverse("v1:post-create"),
            {"kind": "photo", "media": [{"id": str(asset(author).pk)}], "status": "draft"},
            format="json",
            **HEADERS,
        )
        .json()
    )
    url = reverse("v1:post", args=[draft["id"]])
    assert APIClient().get(url).status_code == 404
    assert signed_in(author).get(url).status_code == 200
    mine = signed_in(author).get(reverse("v1:my-posts"), {"status": "draft"}).json()
    assert [p["id"] for p in mine["results"]] == [draft["id"]]
    published = signed_in(author).patch(url, {"status": "published"}, format="json", **HEADERS)
    assert published.json()["status"] == "published"
    assert APIClient().get(url).status_code == 200
    assert signed_in(person(name="X")).delete(url, **HEADERS).status_code == 403
    assert signed_in(author).delete(url, **HEADERS).status_code == 204
    assert APIClient().get(url).status_code == 404


def test_like_save_and_share_counts():
    post = published_post(person())
    client = signed_in(person(name="Awa"))
    liked = client.post(reverse("v1:post-like", args=[post.pk]), **HEADERS).json()
    assert liked == {"like_count": 1, "save_count": 0, "liked": True, "saved": False}
    saved = client.post(reverse("v1:post-save", args=[post.pk]), **HEADERS).json()
    assert saved["saved"] is True
    assert len(client.get(reverse("v1:my-saved")).json()["results"]) == 1
    client.delete(reverse("v1:post-like", args=[post.pk]), **HEADERS)
    links = (
        APIClient()
        .post(
            reverse("v1:post-share", args=[post.pk]),
            {"network": "whatsapp"},
            format="json",
            **HEADERS,
        )
        .json()
    )
    assert links["whatsapp"].startswith("https://wa.me/?text=")
    assert links["facebook"].startswith("https://www.facebook.com/sharer/")
    post.refresh_from_db()
    assert (post.like_count, post.save_count, post.share_count) == (0, 1, 1)


def test_comments_thread_and_visitors_cannot_comment():
    post = published_post(person(name="Aïcha"))
    url = reverse("v1:post-comments", args=[post.pk])
    assert APIClient().post(url, {"text": "Hello"}, format="json", **HEADERS).status_code == 401
    awa = signed_in(person(name="Awa"))
    first = awa.post(url, {"text": "Magnifique"}, format="json", **HEADERS).json()
    signed_in(person(name="Inès")).post(
        url, {"text": "Oui !", "parent_id": first["id"]}, format="json", **HEADERS
    )
    thread = APIClient().get(url).json()["results"]
    assert thread[0]["text"] == "Magnifique" and thread[0]["replies"][0]["text"] == "Oui !"
    assert awa.delete(reverse("v1:comment", args=[first["id"]]), **HEADERS).status_code == 204


def test_someone_without_a_first_name_still_has_a_name():
    post = published_post(person(name="Aïcha"))
    url = reverse("v1:post-comments", args=[post.pk])
    signed_in(person(name="")).post(url, {"text": "Joli"}, format="json", **HEADERS)
    comment = APIClient().get(url, HTTP_ACCEPT_LANGUAGE="fr").json()["results"][0]
    assert comment["author"]["name"] == "Membre Solange Glow"


def test_follow_and_following_list():
    pro = ProFactory(slug="gloria", business_name="Gloria Make-up")
    fan = signed_in(person(name="Awa"))
    url = reverse("v1:person-follow", args=[pro.user.pk])
    assert fan.post(url, **HEADERS).status_code == 204
    following = fan.get(reverse("v1:my-following")).json()
    assert following[0]["name"] == "Gloria Make-up" and following[0]["followed"] is True
    assert fan.delete(url, **HEADERS).status_code == 204
    assert fan.get(reverse("v1:my-following")).json() == []


def test_stories_tray_create_and_seen():
    pro = ProFactory()
    client = signed_in(pro.user)
    created = client.post(
        reverse("v1:stories"),
        {"kind": "free_slots", "slots": ["14:00", "16:30"]},
        format="json",
        **HEADERS,
    )
    assert created.status_code == 201
    viewer = signed_in(person(name="Awa"))
    tray = viewer.get(reverse("v1:stories")).json()
    assert tray[0]["stories"][0]["slots"] == ["14:00", "16:30"]
    assert tray[0]["author"]["has_story"] is True and tray[0]["seen"] is False
    story_id = tray[0]["stories"][0]["id"]
    viewer.post(reverse("v1:story-seen", args=[story_id]), **HEADERS)
    assert viewer.get(reverse("v1:stories")).json()[0]["seen"] is True
    assert client.delete(reverse("v1:story", args=[story_id]), **HEADERS).status_code == 204


def test_reviews_of_a_pro_and_creating_one(bookings):
    pro = ProFactory(slug="aicha", rating_average=None, rating_count=0)
    awa = person(name="Awa")
    booking = bookings.add(awa, pro)
    client = signed_in(awa)
    pending = client.get(reverse("v1:my-pending-reviews")).json()
    assert pending[0]["transaction_id"] == str(booking.id) and pending[0]["pro_slug"] == "aicha"
    created = client.post(
        reverse("v1:review-create"),
        {"kind": "booking", "transaction_id": str(booking.id), "rating": 5, "text": "Parfait"},
        format="json",
        **HEADERS,
    )
    assert created.status_code == 201
    page = APIClient().get(reverse("v1:pro-reviews", args=["aicha"])).json()
    assert page["average"] == 5.0 and page["count"] == 1
    assert page["distribution"]["5"] == 1 and page["results"][0]["author_name"] == "Awa"
    again = client.post(
        reverse("v1:review-create"),
        {"kind": "booking", "transaction_id": str(booking.id), "rating": 1},
        format="json",
        **HEADERS,
    )
    assert again.status_code == 400 and again.json()["code"] == "already_reviewed"
    reply = signed_in(pro.user).post(
        reverse("v1:review-reply", args=[created.json()["id"]]),
        {"text": "Merci Awa !"},
        format="json",
        **HEADERS,
    )
    assert reply.json()["reply"] == "Merci Awa !"


def test_client_rating_by_the_pro(bookings):
    pro = ProFactory()
    booking = bookings.add(person(), pro)
    response = signed_in(pro.user).post(
        reverse("v1:client-rating"),
        {"kind": "booking", "transaction_id": str(booking.id), "rating": 4},
        format="json",
        **HEADERS,
    )
    assert response.status_code == 204


# --- Moderation endpoints ---------------------------------------------------------------------


def test_report_hide_and_block_endpoints():
    author = person(name="Troll")
    post = published_post(author)
    me = signed_in(person(name="Awa"))
    reported = me.post(
        reverse("v1:report"),
        {"target": "post", "id": str(post.pk), "reason": "harassment"},
        format="json",
        **HEADERS,
    )
    assert reported.status_code == 201 and ModerationCase.objects.count() == 1
    me.post(reverse("v1:hide"), {"target": "post", "id": str(post.pk)}, format="json", **HEADERS)
    assert me.get(reverse("v1:feed")).json()["results"] == []
    me.delete(reverse("v1:hide"), {"target": "post", "id": str(post.pk)}, format="json", **HEADERS)
    assert len(me.get(reverse("v1:feed")).json()["results"]) == 1
    me.post(reverse("v1:person-block", args=[author.pk]), **HEADERS)
    assert me.get(reverse("v1:feed")).json()["results"] == []
    assert me.get(reverse("v1:post", args=[post.pk])).status_code == 404
    assert me.get(reverse("v1:my-blocks")).json()[0]["name"] == "Troll"
    unknown = me.post(
        reverse("v1:report"),
        {"target": "post", "id": "00000000-0000-0000-0000-000000000000", "reason": "spam"},
        format="json",
        **HEADERS,
    )
    assert unknown.status_code == 404


def test_a_muted_person_gets_a_clear_refusal():
    author = person()
    moderation.apply_sanction(author, actor=None, level="mute")
    response = signed_in(author).post(
        reverse("v1:post-create"),
        {"kind": "photo", "media": [{"id": str(asset(author).pk)}]},
        format="json",
        **HEADERS,
    )
    assert response.status_code == 403 and response.json()["code"] == "restricted"
    assert Post.objects.count() == 0
