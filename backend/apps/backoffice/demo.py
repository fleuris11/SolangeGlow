"""Demo data of the back office (development only): the owner and a moderator with a
known two-factor secret (used by the e2e captures), prospects, help tickets and a banner."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.content.models import Banner, Ticket
from apps.content.services import help as help_services
from apps.core import crypto

from .models import Prospect, StaffDevice
from .services import team

# Known on purpose: seed_demo refuses to run outside development.
DEMO_PASSWORD = "demo-Glow-2026"  # noqa: S105 - development only
DEMO_SECRET = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"  # noqa: S105 - development only
OWNER_EMAIL = "proprio@solangeglow.test"
MODERATOR_EMAIL = "moderation@solangeglow.test"


def _device(user) -> None:
    StaffDevice.objects.update_or_create(
        user=user,
        defaults={"secret": crypto.encrypt(DEMO_SECRET), "confirmed_at": timezone.now()},
    )


def seed_backoffice() -> dict:
    User = get_user_model()
    team.create_groups()
    owner = User.objects.filter(email=OWNER_EMAIL).first()
    if owner is None:
        owner = User.objects.create_superuser(
            email=OWNER_EMAIL, password=DEMO_PASSWORD, first_name="Solange"
        )
    _device(owner)
    moderator = team.save_member(
        email=MODERATOR_EMAIL,
        first_name="Mireille",
        password=DEMO_PASSWORD,
        roles=["moderation", "support"],
        actor=None,
    )
    _device(moderator)

    prospects = 0
    for name, business, phone, city, trade, status in [
        ("Adjoa", "Adjoa Tresses", "+2290197100001", "Cotonou", "braids", "new"),
        ("Rachida", "Rachida Ongles", "+2290197100002", "Porto-Novo", "nails", "contacted"),
        ("Inès", "Atelier Inès", "+33612340001", "Paris", "sewing", "new"),
    ]:
        _, created = Prospect.objects.get_or_create(
            phone=phone,
            defaults={
                "name": name,
                "business_name": business,
                "city": city,
                "country": "BJ" if phone.startswith("+229") else "FR",
                "trade": trade,
                "status": status,
                "source": "demo",
                "owner": owner,
                "notes": "Vue sur Instagram, très active." if status == "new" else "",
            },
        )
        prospects += created

    if not Ticket.objects.exists():
        for name, email, phone, topic, message in [
            (
                "Grâce",
                "grace@example.com",
                "",
                "booking",
                "Ma coiffeuse n'est pas venue samedi. Comment je récupère mon acompte ?",
            ),
            (
                "Paul",
                "",
                "+2290197100009",
                "payment",
                "J'ai payé par Mobile Money mais la commande dit « en attente ».",
            ),
        ]:
            help_services.create_ticket(
                user=None,
                name=name,
                email=email,
                phone=phone,
                topic=topic,
                message=message,
                language="fr",
            )

    if not Banner.objects.exists():
        Banner.objects.create(
            title_fr="Fête des mères : offre un soin",
            title_en="Mother's Day: give a treat",
            title_sk="Deň matiek: daruj ošetrenie",
            text_fr="Depuis la France, offre une coiffure ou un soin à Cotonou.",
            text_en="From France, give a hairdo or a treat in Cotonou.",
            text_sk="Z Francúzska daruj účes alebo ošetrenie v Cotonou.",
            cta_fr="Offrir",
            cta_en="Give",
            cta_sk="Darovať",
            link="/offrir",
        )
    return {"team": 2, "prospects": prospects}
