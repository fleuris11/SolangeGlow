"""Prospecting: the pros to win over, imported from a file, invited by WhatsApp (SMS when
WhatsApp cannot be used) with a personal sign-up link, followed until they are active."""

from __future__ import annotations

import csv
import io

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core.audit.services import record
from apps.notifications.services import notify_contact

from ..models import Prospect

S = Prospect.Status
COLUMNS = {
    "name": ("name", "nom"),
    "business_name": ("business", "business_name", "activite", "activité", "salon"),
    "phone": ("phone", "telephone", "téléphone", "numero", "numéro"),
    "email": ("email", "e-mail", "mail"),
    "city": ("city", "ville"),
    "country": ("country", "pays"),
    "trade": ("trade", "metier", "métier"),
    "source": ("source",),
}


def _column(header: list[str], aliases: tuple) -> int | None:
    for index, name in enumerate(header):
        if name.strip().lower() in aliases:
            return index
    return None


def import_csv(data: bytes, *, actor, source: str = "") -> dict:
    """Rows added; a phone or e-mail already known is skipped. Commas or semicolons."""
    text = data.decode("utf-8-sig", errors="replace")
    dialect = csv.Sniffer().sniff(text[:2000], delimiters=",;") if text.strip() else csv.excel
    rows = list(csv.reader(io.StringIO(text), dialect))
    if not rows:
        return {"added": 0, "skipped": 0}
    header = rows[0]
    where = {field: _column(header, aliases) for field, aliases in COLUMNS.items()}
    if where["name"] is None and where["business_name"] is None:
        return {"added": 0, "skipped": len(rows) - 1, "error": "name"}
    added = skipped = 0
    with transaction.atomic():
        for row in rows[1:]:
            values = {
                field: (row[index].strip() if index is not None and index < len(row) else "")
                for field, index in where.items()
            }
            if not (values["name"] or values["business_name"]):
                skipped += 1
                continue
            known = Prospect.objects.none()
            if values["phone"]:
                known = Prospect.objects.filter(phone=values["phone"])
            if values["email"] and not known.exists():
                known = Prospect.objects.filter(email__iexact=values["email"])
            if known.exists():
                skipped += 1
                continue
            Prospect.objects.create(
                name=(values["name"] or values["business_name"])[:150],
                business_name=values["business_name"][:150],
                phone=values["phone"][:30],
                email=values["email"][:254],
                city=values["city"][:80],
                country=(values["country"] or "BJ")[:2].upper(),
                trade=values["trade"][:40],
                source=(values["source"] or source)[:80],
                owner=actor,
            )
            added += 1
    record("backoffice.prospects_imported", None, actor=actor, metadata={"added": added})
    return {"added": added, "skipped": skipped}


def link_of(prospect: Prospect) -> str:
    return f"{settings.SITE_URL.rstrip('/')}/fr/pro/start?invite={prospect.invite_code}"


def invite(prospect: Prospect, *, actor) -> bool:
    """Sends the invitation (editable template « prospects.invitation »)."""
    if not prospect.phone:
        return False
    sent = notify_contact(
        prospect.phone,
        "prospects.invitation",
        {"name": prospect.name.split(" ")[0], "link": link_of(prospect)},
    )
    if sent is None:
        return False
    prospect.invited_at = timezone.now()
    if prospect.status == S.NEW:
        prospect.status = S.CONTACTED
    prospect.save(update_fields=["invited_at", "status", "updated_at"])
    record("backoffice.prospect_invited", prospect, actor=actor)
    return True


@transaction.atomic
def claim(user, code: str) -> Prospect | None:
    """A pro signed up with the link of her invitation."""
    found = Prospect.objects.select_for_update().filter(invite_code=(code or "").strip()).first()
    if found is None or found.status in (S.ACTIVE, S.DECLINED):
        return None
    found.signed_up_user = user
    found.status = S.SIGNED_UP
    found.save(update_fields=["signed_up_user", "status", "updated_at"])
    record("backoffice.prospect_signed_up", found, actor=user)
    return found


def promote_active() -> int:
    """Celery Beat, every night: a signed-up prospect whose showcase is published is active."""
    from apps.pros.models import ProProfile

    published = ProProfile.objects.filter(status=ProProfile.Status.PUBLISHED).values("user_id")
    return Prospect.objects.filter(status=S.SIGNED_UP, signed_up_user_id__in=published).update(
        status=S.ACTIVE, updated_at=timezone.now()
    )
