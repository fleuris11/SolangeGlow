"""Demo academy (development only, idempotent): courses of the platform (one free that gives
the badge, one in the pass), a paid course of Institut Prisca, a course of Fatou Braids
waiting for review, two lives. Every lesson shows the same generated video (3 min)."""

from __future__ import annotations

import datetime
import subprocess
import tempfile
import uuid
from pathlib import Path

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.core.media.models import MediaAsset
from apps.core.media.processing import process
from apps.core.models import Country
from apps.pros.models import ProProfile, Trade

from . import selectors
from .models import Course, Lesson, LiveSession, Module, Question

DEMO_VIDEO = "demo-lesson.mp4"
SECONDS = 185  # a little above the 3 minutes of the shortest lesson

COURSES = [
    {
        "slug": "hygiene-et-securite-au-salon",
        "platform": "BJ",
        "title": "Hygiène et sécurité au salon",
        "summary": "Les gestes qui protègent tes clientes et toi, chaque jour.",
        "trade": "hair",
        "level": "beginner",
        "pricing": "free",
        "badge": True,
        "modules": [
            ("Un poste propre", ["Désinfecter ses outils", "Le linge et les serviettes"]),
            ("Protéger sa cliente", ["Allergies : le test de 48 h", "Les produits à éviter"]),
        ],
    },
    {
        "slug": "gerer-sa-clientele-sur-whatsapp",
        "platform": "BJ",
        "title": "Gérer sa clientèle sur WhatsApp",
        "summary": "Répondre vite, confirmer les rendez-vous, fidéliser sans y passer la nuit.",
        "trade": None,
        "level": "intermediate",
        "pricing": "pass",
        "modules": [
            ("Bien démarrer", ["Un profil qui inspire confiance", "Les réponses rapides"]),
        ],
    },
    {
        "slug": "les-bases-de-la-colorimetrie",
        "platform": "FR",
        "title": "Les bases de la colorimétrie",
        "summary": "Choisir les teintes qui subliment chaque carnation.",
        "trade": "makeup",
        "level": "beginner",
        "pricing": "free",
        "modules": [("Comprendre les sous-tons", ["Chaud, froid, neutre", "Le test du bijou"])],
    },
    {
        "slug": "maquillage-mariee-en-5-etapes",
        "pro": "institut-prisca",
        "title": "Maquillage mariée en 5 étapes",
        "summary": "Un teint qui tient toute la journée, même sous la chaleur de Cotonou.",
        "trade": "makeup",
        "level": "intermediate",
        "pricing": "paid",
        "price": 5000,
        "modules": [
            ("Préparer la peau", ["Nettoyer et hydrater", "La base qui fixe"]),
            ("Le teint", ["Fond de teint et correcteur", "Poudrer sans figer"]),
        ],
    },
    {
        "slug": "tresses-collees-pour-debutantes",
        "pro": "fatou-braids",
        "title": "Tresses collées pour débutantes",
        "summary": "Des raies nettes et des tresses régulières, pas à pas.",
        "trade": "braids",
        "level": "beginner",
        "pricing": "paid",
        "price": 3000,
        "review": True,
        "modules": [("Les raies", ["Tracer une raie droite", "Tenir la tension"])],
    },
]

QUIZ = [
    ("Combien de temps attendre après un test d'allergie ?", ["2 heures", "48 heures"], 1),
    ("On désinfecte ses outils…", ["Une fois par semaine", "Après chaque cliente"], 1),
]


def _video(owner) -> MediaAsset | None:
    """One real video (3 minutes, brand colour, quiet tone), processed once."""
    found = MediaAsset.objects.filter(
        original_name=DEMO_VIDEO, purpose="lesson_video", status=MediaAsset.Status.READY
    ).first()
    if found is not None:
        return found
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / DEMO_VIDEO
        command = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c=0xF6E3E8:s=640x360:r=10:d={SECONDS}",
            "-f", "lavfi", "-i", f"sine=frequency=330:duration={SECONDS}",
            "-af", "volume=0.05", "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac", "-shortest", str(path),
        ]  # fmt: skip
        try:
            subprocess.run(command, check=True, timeout=300)  # noqa: S603 - fixed arguments
        except (OSError, subprocess.SubprocessError):
            return None
        data = path.read_bytes()
    asset = MediaAsset(
        id=uuid.uuid4(),
        owner=owner,
        kind=MediaAsset.Kind.VIDEO,
        purpose="lesson_video",
        visibility=MediaAsset.Visibility.PRIVATE,
        original_name=DEMO_VIDEO,
        content_type="video/mp4",
        size_bytes=len(data),
    )
    asset.original.save(DEMO_VIDEO, ContentFile(data), save=False)
    asset.save()
    process(asset)
    return asset if asset.is_ready else None


def _course(data: dict, video: MediaAsset) -> Course | None:
    if Course.objects.filter(slug=data["slug"]).exists():
        return None
    if "pro" in data:
        pro = ProProfile.objects.filter(slug=data["pro"]).select_related("user", "country").first()
        if pro is None or pro.country is None:
            return None
        country, author = pro.country, pro.user
    else:
        pro = None
        country = (
            Country.objects.select_related("default_currency").filter(code=data["platform"]).first()
        )
        if country is None:
            return None
        author = selectors.house_account(country)
    now = timezone.now()
    review = data.get("review", False)
    course = Course.objects.create(
        slug=data["slug"],
        pro=pro,
        author=author,
        country=country,
        title=data["title"],
        summary=data["summary"],
        description=data["summary"],
        trade=Trade.objects.filter(key=data["trade"]).first() if data["trade"] else None,
        level=data["level"],
        pricing=data["pricing"],
        price_minor=data.get("price", 0),
        currency=(pro.currency if pro and pro.currency else selectors.currency_of(country)),
        status=Course.Status.IN_REVIEW if review else Course.Status.PUBLISHED,
        submitted_at=now if review else None,
        published_at=None if review else now,
        counts_for_badge=data.get("badge", False),
    )
    for index, (title, lessons) in enumerate(data["modules"]):
        module = Module.objects.create(course=course, title=title, position=index)
        for position, lesson in enumerate(lessons):
            Lesson.objects.create(
                module=module,
                title=lesson,
                video=video,
                duration_seconds=int(video.duration_seconds or SECONDS),
                is_preview=index == 0 and position == 0,
                position=position,
            )
        if data.get("badge"):
            for position, (text, choices, correct) in enumerate(QUIZ):
                Question.objects.create(
                    module=module, text=text, choices=choices, correct=correct, position=position
                )
    course.duration_seconds = sum(
        lesson.duration_seconds for lesson in Lesson.objects.filter(module__course=course)
    )
    course.save(update_fields=["duration_seconds"])
    return course


def _lives() -> int:
    if LiveSession.objects.exists():
        return 0
    now = timezone.now().replace(minute=0, second=0, microsecond=0)
    count = 0
    benin = Country.objects.filter(code="BJ").first()
    if benin is not None:
        LiveSession.objects.create(
            author=selectors.house_account(benin),
            country=benin,
            title="Bien démarrer sur Solange Glow",
            description="Questions-réponses avec l'équipe : vitrine, rendez-vous, paiements.",
            starts_at=now + datetime.timedelta(days=3, hours=2),
            duration_minutes=60,
            capacity=200,
        )
        count += 1
    prisca = ProProfile.objects.filter(slug="institut-prisca").select_related("user").first()
    course = Course.objects.filter(slug="maquillage-mariee-en-5-etapes").first()
    if prisca is not None and prisca.country is not None:
        LiveSession.objects.create(
            pro=prisca,
            author=prisca.user,
            country=prisca.country,
            course=course,
            title="Maquillage mariée : vos questions",
            starts_at=now + datetime.timedelta(days=5, hours=3),
            duration_minutes=45,
            capacity=50,
        )
        count += 1
    return count


def seed_academy() -> dict:
    counts = {"courses": 0, "lives": 0}
    benin = Country.objects.filter(code="BJ").first()
    if benin is None:
        return counts
    video = _video(selectors.house_account(benin))
    if video is None:
        return counts
    with transaction.atomic():
        for data in COURSES:
            if _course(data, video) is not None:
                counts["courses"] += 1
        counts["lives"] = _lives()
    return counts
