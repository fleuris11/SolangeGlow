"""Prospecting: the pros to win over, imported from a file, invited by WhatsApp (SMS when
WhatsApp cannot be used) with a personal sign-up link, followed until they are active."""

from __future__ import annotations

import csv
import io

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core.audit.services import record
from apps.core.selectors import get_setting
from apps.notifications.services import notify_contact

from .. import errors
from ..models import Prospect, ProspectEmailTemplate, ProspectMessage

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
                language=default_language(values["country"] or "BJ"),
                trade=values["trade"][:40],
                source=(values["source"] or source)[:80],
                owner=actor,
            )
            added += 1
    record("backoffice.prospects_imported", None, actor=actor, metadata={"added": added})
    return {"added": added, "skipped": skipped}


def link_of(prospect: Prospect) -> str:
    return signup_link(prospect)


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


# --- Prospecting by e-mail, with a showcase prepared for them ---------------------------------
#
# The team prepares a draft showcase for a professional (nothing public), then e-mails her a
# personal link: she chooses her password, sees her showcase, corrects it and puts it online
# herself. Every e-mail carries a « not interested » link, and a prospect who used it is never
# written to again.

FRENCH_SPEAKING = {"FR", "BJ", "BE", "CH", "LU", "MC", "CI", "SN", "TG", "CM", "GA", "ML", "BF"}


def default_language(country: str) -> str:
    code = (country or "").upper()
    if code == "SK":
        return "sk"
    return "fr" if code in FRENCH_SPEAKING else "en"


def signup_link(prospect: Prospect) -> str:
    base = settings.SITE_URL.rstrip("/")
    return f"{base}/{prospect.language}/pro/start?invite={prospect.invite_code}"


def stop_link(prospect: Prospect) -> str:
    return f"{settings.SITE_URL.rstrip('/')}/api/v1/prospects/{prospect.invite_code}/stop"


@transaction.atomic
def prepare_showcase(prospect: Prospect, *, actor):
    """Creates her account (no password yet) and a draft showcase from what we know of her.

    Nothing is public: she alone puts it online, after choosing her password with the link of
    the e-mail. The team completes the draft by signing in as her (photos, services)."""
    from apps.accounts.models import SignupChannel, User
    from apps.core.models import Country
    from apps.pros import services as pro_services

    prospect = Prospect.objects.select_for_update().get(pk=prospect.pk)
    if prospect.pro_id:
        return prospect.pro
    email = (prospect.email or "").strip().lower()
    if not email:
        raise errors.ProspectEmailNeeded()
    if User.objects.filter(email__iexact=email).exists():
        raise errors.ProspectAccountExists()
    country = Country.objects.filter(code=prospect.country.upper(), is_active=True).first()
    user = User.objects.create_user(
        email=email,
        first_name=prospect.name.split(" ")[0][:150],
        signup_channel=SignupChannel.ADMIN,
        preferred_language=prospect.language,
        country=country,
        preferred_currency=country.default_currency if country else None,
        city=prospect.city[:80],
    )
    pro = pro_services.become_pro(
        user,
        business_name=prospect.business_name or prospect.name,
        trade_keys=[prospect.trade] if prospect.trade else None,
        city=prospect.city,
    )
    if prospect.services and not pro.bio:
        pro.bio = prospect.services.strip()[:1000]
        pro.save(update_fields=["bio", "updated_at"])
    prospect.pro = pro
    prospect.save(update_fields=["pro", "updated_at"])
    record("backoffice.prospect_showcase_prepared", prospect, actor=actor)
    return pro


def _text(template: ProspectEmailTemplate, field: str, language: str) -> str:
    return getattr(template, f"{field}_{language}", "") or getattr(template, field)


def compose(prospect: Prospect, template: ProspectEmailTemplate) -> tuple[str, str]:
    """Subject and text of a standard e-mail for this prospect, in her language."""
    from django.template import Context, Template

    from apps.accounts import services as account_services

    if template.needs_showcase:
        if not prospect.pro_id:
            raise errors.ShowcaseNeeded()
        link = account_services.link_url(prospect.pro.user, "invite")
    else:
        link = signup_link(prospect)
    context = Context(
        {
            "name": prospect.name.split(" ")[0],
            "business": prospect.business_name or prospect.name,
            "city": prospect.city,
            "pitch": prospect.pitch.strip(),
            "link": link,
            "stop_link": stop_link(prospect),
        },
        autoescape=False,
    )
    subject = Template(_text(template, "subject", prospect.language)).render(context)
    body = Template(_text(template, "body", prospect.language)).render(context)
    # An empty {{ pitch }} leaves a hole: never more than one empty line in a row.
    while "\n\n\n" in body:
        body = body.replace("\n\n\n", "\n\n")
    return " ".join(subject.split())[:200], body.strip() + "\n"


def sent_today() -> int:
    start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return ProspectMessage.objects.filter(created_at__gte=start).count()


@transaction.atomic
def send_email(prospect: Prospect, template: ProspectEmailTemplate, *, actor) -> ProspectMessage:
    """Queues a standard e-mail (it leaves in the background, with retries) and follows it."""
    from ..tasks import send_prospect_message

    if prospect.status == S.DECLINED:
        raise errors.ProspectDeclined()
    if not (prospect.email or "").strip():
        raise errors.ProspectEmailNeeded()
    most = int(get_setting("prospects.daily_email_limit", default=100))
    if most and sent_today() >= most:
        raise errors.DailyEmailLimit(details={"max": most})
    subject, body = compose(prospect, template)
    message = ProspectMessage.objects.create(
        prospect=prospect,
        template_key=template.key,
        to_email=prospect.email.strip().lower(),
        subject=subject,
        body=body,
        sent_by=actor,
    )
    now = timezone.now()
    prospect.last_message_at = now
    prospect.invited_at = prospect.invited_at or now
    if prospect.status == S.NEW:
        prospect.status = S.CONTACTED
    prospect.save(update_fields=["last_message_at", "invited_at", "status", "updated_at"])
    record("backoffice.prospect_emailed", prospect, actor=actor, metadata={"key": template.key})
    transaction.on_commit(lambda: send_prospect_message.delay(str(message.pk)))
    return message


def deliver(message_id: str) -> str:
    """Sends one queued e-mail. Raises when the e-mail service refuses (the task retries)."""
    from django.core.mail import EmailMessage

    message = ProspectMessage.objects.select_related("prospect").filter(pk=message_id).first()
    if message is None or message.status == ProspectMessage.Status.SENT:
        return "skipped"
    if message.prospect.status == S.DECLINED:
        mark_failed(message_id, "declined")
        return "declined"
    reply_to = (get_setting("prospects.reply_to", default="") or "").strip()
    EmailMessage(
        message.subject,
        message.body,
        settings.DEFAULT_FROM_EMAIL,
        [message.to_email],
        reply_to=[reply_to] if reply_to else None,
    ).send()
    message.status = ProspectMessage.Status.SENT
    message.sent_at = timezone.now()
    message.error = ""
    message.save(update_fields=["status", "sent_at", "error", "updated_at"])
    return "sent"


def mark_failed(message_id: str, reason: str) -> None:
    ProspectMessage.objects.filter(pk=message_id).exclude(
        status=ProspectMessage.Status.SENT
    ).update(status=ProspectMessage.Status.FAILED, error=reason[:200], updated_at=timezone.now())


def decline(code: str) -> bool:
    """« Not interested »: the link at the bottom of every e-mail. She is never written again."""
    found = Prospect.objects.filter(invite_code=(code or "").strip()).first()
    if found is None:
        return False
    if found.status != S.DECLINED:
        found.status = S.DECLINED
        found.save(update_fields=["status", "updated_at"])
        record("backoffice.prospect_declined", found, actor=None)
    return True


def on_password_chosen(user) -> None:
    """She opened the link and chose her password: the prospect is signed up."""
    Prospect.objects.filter(pro__user=user, status__in=[S.NEW, S.CONTACTED]).update(
        status=S.SIGNED_UP, signed_up_user=user, updated_at=timezone.now()
    )
