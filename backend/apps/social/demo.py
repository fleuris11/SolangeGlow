"""Demo social content (called by `seed_demo`): posts, stories, likes, comments, follows, reviews.

Pictures are drawn by demo_art and processed by the media pipeline right away. Texts are
content written in French, as a pro or a client of Cotonou or Paris would. Idempotent:
posts are created once; stories are renewed when none is live (they last 24 hours).
"""

from __future__ import annotations

import datetime
import random
import uuid

from django.core.files.base import ContentFile
from django.utils import timezone

from apps.accounts.models import User
from apps.core.media.models import MediaAsset
from apps.core.media.processing import process
from apps.pros.models import ProProfile

from . import demo_art
from .models import Comment, Follow, Like, Post, PostMedia, Review, SavedPost, Story
from .services import recompute_rating

CAPTIONS = {
    "braids": [
        "Knotless mi-dos pour la rentrée. 5 h de patience, un résultat qui tient 6 semaines.",
        "Nattes collées pour la petite Grâce, prête pour l'école !",
        "Box braids longues, mèches fournies. Réserve ton créneau du samedi.",
    ],
    "hair": [
        "Défrisage + brushing : des cheveux doux et brillants.",
        "Chignon de cérémonie pour un mariage à Akpakpa.",
        "Soin profond pour cheveux crépus : on hydrate avant tout.",
    ],
    "makeup": [
        "Maquillage de soirée, teint lumineux pour peau foncée.",
        "Mariée du jour, maquillage qui tient jusqu'au bout de la nuit.",
    ],
    "nails": [
        "Pose gel couleur or et nail art wax.",
        "Manucure nude pour un look élégant au bureau.",
    ],
    "headwrap": [
        "Gèle de mariage en aso-oke, attaché en 20 minutes.",
        "Attache de foulard pour le baptême de dimanche.",
    ],
    "sewing": [
        "Robe en pagne sur mesure, coupe sirène.",
        "Ensemble wax pour toute la famille, livré en une semaine.",
    ],
    "skincare": [
        "Soin visage éclat : la peau respire.",
        "Routine du soir pour peau mixte, produits naturels.",
    ],
}
COMMENTS = [
    "Trop beau !",
    "Je réserve la semaine prochaine 😍",
    "Combien de temps ça tient ?",
    "Magnifique travail, bravo",
    "C'est exactement ce que je cherchais",
    "Tu te déplaces à Calavi ?",
    "Le résultat est top !",
    "J'adore la couleur",
]
REPLIES = [
    "Merci beaucoup !",
    "Oui, écris-moi pour réserver",
    "Environ 6 semaines avec un bon entretien",
]
REVIEWS = [
    (5, "Très professionnelle et douce. Mes tresses sont parfaites."),
    (5, "Ponctuelle, propre, et le résultat est encore plus beau qu'en photo."),
    (4, "Très beau travail, juste un peu d'attente au début."),
    (5, "Je recommande les yeux fermés."),
    (4, "Bon accueil, prix honnête."),
]
STORY_TEXTS = [
    ("-20 % sur les tresses enfant ce samedi !", "or"),
    ("Nouveau : pose gel à domicile à Cotonou", "hibiscus"),
    ("Je suis en formation lundi, salon fermé", "prune"),
]


def _picture(owner, seed: str, trade: str, *, stage="after", purpose="post") -> MediaAsset:
    """A demo picture stored and processed now (no Celery round trip)."""
    asset = MediaAsset(
        id=uuid.uuid4(),
        owner=owner,
        kind=MediaAsset.Kind.IMAGE,
        purpose=purpose,
        visibility=MediaAsset.Visibility.PUBLIC,
        original_name=f"{seed}.jpg",
        content_type="image/jpeg",
    )
    data = demo_art.picture(seed, trade, stage=stage)
    asset.size_bytes = len(data)
    asset.original.save(f"{seed}.jpg", ContentFile(data), save=False)
    asset.save()
    process(asset)
    return asset


def _trade_of(pro: ProProfile) -> str:
    first = pro.trades.first()
    return first.key if first else "hair"


def seed_social(rng: random.Random | None = None) -> dict:
    rng = rng or random.Random(42)  # noqa: S311  (demo data)
    counts = {"posts": 0, "stories": 0, "reviews": 0}
    pros = list(
        ProProfile.objects.filter(status=ProProfile.Status.PUBLISHED)
        .select_related("user", "country")
        .order_by("slug")
    )
    clients = list(User.objects.filter(pro_profile__isnull=True, is_active=True, is_staff=False))
    people = [p.user for p in pros] + clients
    if not pros:
        return counts
    now = timezone.now()

    if not Post.objects.filter(author__in=[p.user for p in pros]).exists():
        for index, pro in enumerate(pros):
            trade = _trade_of(pro)
            services = list(pro.services.filter(is_active=True)[:3])
            for number in range(1 + index % 2):
                seed = f"{pro.slug}-{number}"
                kind = ["photo", "before_after", "carousel"][(index + number) % 3]
                if kind == "before_after" and trade in ("nails", "sewing"):
                    kind = "photo"
                post = Post.objects.create(
                    author=pro.user,
                    pro=pro,
                    kind=kind,
                    caption=rng.choice(CAPTIONS.get(trade, CAPTIONS["hair"])),
                    trade=pro.trades.first(),
                    service=services[number % len(services)] if services else None,
                    status=Post.Status.PUBLISHED,
                    published_at=now - datetime.timedelta(hours=rng.randint(2, 24 * 12)),
                    city=pro.city,
                    country=pro.country,
                    location=pro.location,
                )
                if kind == "before_after":
                    items = [
                        (_picture(pro.user, seed + "-b", trade, stage="before"), "before"),
                        (_picture(pro.user, seed, trade), "after"),
                    ]
                elif kind == "carousel":
                    items = [(_picture(pro.user, f"{seed}-{i}", trade), "item") for i in range(3)]
                else:
                    items = [(_picture(pro.user, seed, trade), "item")]
                PostMedia.objects.bulk_create(
                    PostMedia(post=post, media=media, role=role, position=position)
                    for position, (media, role) in enumerate(items)
                )
                counts["posts"] += 1

                fans = rng.sample(people, k=min(len(people), rng.randint(3, 14)))
                for fan in fans:
                    if fan != pro.user:
                        Like.objects.get_or_create(user=fan, post=post)
                for fan in fans[:2]:
                    if fan != pro.user:
                        SavedPost.objects.get_or_create(user=fan, post=post)
                for fan in fans[: rng.randint(0, 3)]:
                    if fan == pro.user:
                        continue
                    first = Comment.objects.create(post=post, author=fan, text=rng.choice(COMMENTS))
                    if rng.random() < 0.6:
                        Comment.objects.create(
                            post=post, author=pro.user, parent=first, text=rng.choice(REPLIES)
                        )
                Post.objects.filter(pk=post.pk).update(
                    like_count=post.likes.count(),
                    save_count=post.saves.count(),
                    comment_count=post.comments.count(),
                    share_count=rng.randint(0, 6),
                )

        for person in people:
            for pro in rng.sample(pros, k=min(len(pros), rng.randint(3, 8))):
                if pro.user != person:
                    Follow.objects.get_or_create(follower=person, followed=pro.user)

        for pro in pros:
            authors = [c for c in clients if c != pro.user] or [p.user for p in pros if p != pro]
            for rating, text in rng.sample(REVIEWS, k=min(len(REVIEWS), rng.randint(1, 3))):
                Review.objects.create(
                    author=rng.choice(authors),
                    pro=pro,
                    source_type="booking",  # demo bookings, before the booking module exists
                    source_id=uuid.uuid4(),
                    rating=rating,
                    text=text,
                    reply="Merci pour ta confiance, à bientôt !" if rng.random() < 0.5 else "",
                    replied_at=now if rng.random() < 0.5 else None,
                )
                counts["reviews"] += 1
            recompute_rating(pro.pk)

    if not Story.objects.filter(expires_at__gt=now).exists():
        expires = now + datetime.timedelta(hours=24)
        for pro in pros[:6]:
            slots = sorted(rng.sample(["10:00", "11:30", "14:00", "15:30", "17:00", "18:30"], 3))
            Story.objects.create(
                author=pro.user,
                pro=pro,
                kind=Story.Kind.FREE_SLOTS,
                slots=slots,
                expires_at=expires,
                city=pro.city,
                country=pro.country,
            )
            counts["stories"] += 1
        for pro, (text, background) in zip(pros[6:9], STORY_TEXTS, strict=False):
            Story.objects.create(
                author=pro.user,
                pro=pro,
                kind=Story.Kind.TEXT,
                text=text,
                background=background,
                expires_at=expires,
                city=pro.city,
                country=pro.country,
            )
            counts["stories"] += 1
        for pro in pros[9:12]:
            Story.objects.create(
                author=pro.user,
                pro=pro,
                kind=Story.Kind.PHOTO,
                media=_picture(pro.user, f"story-{pro.slug}", _trade_of(pro), purpose="story"),
                expires_at=expires,
                city=pro.city,
                country=pro.country,
            )
            counts["stories"] += 1
    return counts
