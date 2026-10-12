import datetime
import uuid

from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.core.media.models import MediaAsset
from apps.core.tests.factories import CountryFactory
from apps.social.eligibility import Transaction
from apps.social.models import Post, PostMedia


def person(name="Awa", city="Cotonou", **kwargs):
    kwargs.setdefault("country", CountryFactory())
    return UserFactory(first_name=name, city=city, **kwargs)


def asset(owner, kind="image", purpose="post") -> MediaAsset:
    """A processed media, without running the pipeline."""
    variants = (
        {"medium": {"path": f"{kind}/x/medium.webp"}, "thumb": {"path": f"{kind}/x/thumb.webp"}}
        if kind == "image"
        else {"low": {"path": "video/x/low.mp4"}, "poster_medium": {"path": "video/x/p.webp"}}
        if kind == "video"
        else {"voice": {"path": "audio/x/voice.webm"}}
    )
    return MediaAsset.objects.create(
        owner=owner,
        kind=kind,
        purpose=purpose,
        visibility="public",
        status=MediaAsset.Status.READY,
        variants=variants,
        width=800,
        height=1000,
    )


def published_post(author, *, hours_ago=1, likes=0, city=None, caption="Knotless", **kwargs):
    post = Post.objects.create(
        author=author,
        kind=Post.Kind.PHOTO,
        caption=caption,
        status=Post.Status.PUBLISHED,
        published_at=timezone.now() - datetime.timedelta(hours=hours_ago),
        city=city if city is not None else author.city,
        country=author.country,
        like_count=likes,
        **kwargs,
    )
    PostMedia.objects.create(post=post, media=asset(author))
    return post


class FakeBookings:
    """Stands for the booking module: finished bookings that open the right to a review."""

    kind = "booking"

    def __init__(self):
        self.items: dict[uuid.UUID, Transaction] = {}

    def add(self, client, pro, *, finished_days_ago=1, finished=True) -> Transaction:
        item = Transaction(
            kind="booking",
            id=uuid.uuid4(),
            client_id=client.pk,
            pro_id=pro.pk,
            finished_at=timezone.now() - datetime.timedelta(days=finished_days_ago)
            if finished
            else None,
            label="Knotless mi-dos",
        )
        self.items[item.id] = item
        return item

    def get(self, transaction_id):
        return self.items.get(transaction_id)

    def finished_for_client(self, client_id):
        return [t for t in self.items.values() if t.client_id == client_id and t.finished_at]

    def finished_for_pro(self, pro_id):
        return [t for t in self.items.values() if t.pro_id == pro_id and t.finished_at]
