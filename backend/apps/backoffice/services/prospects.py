"""Prospecting: the pros to win over, imported from a file, invited by WhatsApp (SMS when
WhatsApp cannot be used) with a personal sign-up link, followed until they are active."""

from __future__ import annotations

import csv
import io

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core.audit.services import record
from apps.core.errors import DomainError
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


# --- Prospecting with a showcase prepared for them --------------------------------------------
#
# The team prepares the showcase of a professional from what they already show (name, trade,
# address, photos of their work, their WhatsApp), puts it online to put their work forward,
# then writes to them (e-mail or WhatsApp) with a personal link: they choose their password
# and the page is theirs. Until then the page says it was prepared by the team, sends clients
# to their own WhatsApp (no online booking) and can be removed in one click. Every message
# carries a « not interested » link, and a prospect who used it is never written to again.

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

    given, prospect = prospect, Prospect.objects.select_for_update().get(pk=prospect.pk)
    if prospect.pro_id:
        given.pro = prospect.pro
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
    changes = {}
    if prospect.address.strip():
        changes.update(address=prospect.address.strip()[:200], receives_clients=True)
    if prospect.services.strip():
        changes["bio"] = prospect.services.strip()[:1000]
    links = social_links(prospect)
    try:
        pro = pro_services.update_profile(pro, actor=actor, social_links=links, **changes)
    except DomainError:
        # A page we cannot read is left out; their WhatsApp is enough to reach them.
        links = {k: v for k, v in links.items() if k == "whatsapp"}
        pro = pro_services.update_profile(pro, actor=actor, social_links=links, **changes)
    pro.prepared_by_team = True
    pro.save(update_fields=["prepared_by_team", "updated_at"])
    _pause_online_booking(pro)
    prospect.pro = given.pro = pro
    prospect.save(update_fields=["pro", "updated_at"])
    record("backoffice.prospect_showcase_prepared", prospect, actor=actor)
    return pro


def _pause_online_booking(pro) -> None:
    """Clients cannot book with someone who does not know the page yet: they write on WhatsApp.
    The professional switches online booking on once the page is theirs."""
    from apps.booking.models import BookingSettings
    from apps.booking.services import common as booking_common

    BookingSettings.objects.update_or_create(pro=pro, defaults={"online_paused": True})
    booking_common.changed(pro)


def whatsapp_number(prospect: Prospect) -> str:
    """Their number with the country code, digits only (as WhatsApp links want it), or ""."""
    import phonenumbers

    raw = (prospect.phone or "").strip()
    if not raw:
        return ""
    try:
        number = phonenumbers.parse(raw, (prospect.country or "BJ").upper())
    except phonenumbers.NumberParseException:
        return ""
    if not phonenumbers.is_possible_number(number):
        return ""
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164).lstrip("+")


NETWORKS = ("instagram", "tiktok", "facebook", "youtube")


def social_links(prospect: Prospect) -> dict:
    """Their WhatsApp and their page (Instagram, Facebook… or their site), for the showcase."""
    links = {}
    number = whatsapp_number(prospect)
    if number:
        links["whatsapp"] = "+" + number
    site = (prospect.website or "").strip()
    if not site:
        return links
    lowered = site.lower()
    network = next((n for n in NETWORKS if f"{n}.com" in lowered), None)
    if network:
        links[network] = site if lowered.startswith("http") else f"https://{site}"
    elif site.startswith("@"):
        links["instagram"] = site
    else:
        links["website"] = site if lowered.startswith("http") else f"https://{site}"
    return links


def showcase_link(prospect: Prospect) -> str:
    """The public address of their showcase, once it is online."""
    from apps.pros.models import ProProfile

    pro = prospect.pro
    if pro is None or pro.status != ProProfile.Status.PUBLISHED or not pro.slug:
        return ""
    return f"{settings.SITE_URL.rstrip('/')}/{prospect.language}/{pro.slug}"


@transaction.atomic
def publish_showcase(prospect: Prospect, *, actor):
    """Puts the prepared showcase online. Raises NotReadyToPublish with what is missing."""
    from apps.pros import services as pro_services

    given, prospect = prospect, Prospect.objects.select_for_update().get(pk=prospect.pk)
    if prospect.status == S.DECLINED:
        raise errors.ProspectDeclined()
    if not prospect.pro_id:
        raise errors.ShowcaseNotPrepared()
    pro = given.pro = pro_services.publish(prospect.pro, actor=actor)
    record("backoffice.prospect_showcase_published", prospect, actor=actor)
    return pro


def activity(prospect: Prospect) -> str:
    """« Hairdressing, Cotonou »: their trade in their language, and their city."""
    from django.utils import translation

    from apps.pros.models import Trade

    trade = ""
    if prospect.trade:
        found = Trade.objects.filter(key=prospect.trade).first()
        if found is not None:
            with translation.override(prospect.language):
                trade = found.name
        else:
            trade = prospect.trade
    return ", ".join(part for part in (trade, prospect.city.strip()) if part)


def personal_link(prospect: Prospect) -> str:
    """With a prepared showcase not taken yet: the link to choose a password (single use).
    Otherwise: the sign-up link of their invitation."""
    from apps.accounts import services as account_services

    if prospect.pro_id and not prospect.pro.user.has_usable_password():
        return account_services.link_url(prospect.pro.user, "invite")
    return signup_link(prospect)


def whatsapp_text(prospect: Prospect) -> str:
    """The message written for them, in their language, sent from the team's own WhatsApp."""
    from django.utils import translation
    from django.utils.translation import gettext as _

    values = {
        "name": prospect.name.split(" ")[0],
        "business": prospect.business_name or prospect.name,
        "activity": activity(prospect) or prospect.city or "Solange Glow",
        "showcase": showcase_link(prospect),
        "link": personal_link(prospect),
    }
    with translation.override(prospect.language):
        if values["showcase"]:
            text = _(
                "Hello %(name)s, I am writing from Solange Glow, the beauty and fashion platform. "
                "We put the work of %(business)s (%(activity)s) forward on our site, in your "
                "name, with your contact: %(showcase)s\n\n"
                "This page is yours. Choose your password to change it, add your services and "
                "receive your bookings, free: %(link)s\n\n"
                "If you prefer that we remove it, just tell me."
            )
        else:
            text = _(
                "Hello %(name)s, I am writing from Solange Glow, the beauty and fashion platform. "
                "We would like to put the work of %(business)s (%(activity)s) forward: a "
                "showcase in your name, online bookings and our advertising, free.\n\n"
                "Create your showcase in a few minutes: %(link)s"
            )
    return text % values


def mark_written(prospect: Prospect, *, actor, channel: str) -> None:
    """The team opened WhatsApp with the message for them: contacted, written in the journal."""
    now = timezone.now()
    prospect.invited_at = prospect.invited_at or now
    if prospect.status == S.NEW:
        prospect.status = S.CONTACTED
    prospect.save(update_fields=["invited_at", "status", "updated_at"])
    record("backoffice.prospect_written", prospect, actor=actor, metadata={"channel": channel})


def whatsapp_to_prospect(prospect: Prospect) -> str:
    """Opens WhatsApp on their number with the message already written. "" without a number."""
    from urllib.parse import quote

    number = whatsapp_number(prospect)
    if not number:
        return ""
    return f"https://wa.me/{number}?text={quote(whatsapp_text(prospect))}"


def whatsapp_share(prospect: Prospect) -> str:
    """Opens WhatsApp to share their showcase (status, groups) with a text ready."""
    from urllib.parse import quote

    from django.utils import translation
    from django.utils.translation import gettext as _

    link = showcase_link(prospect)
    if not link:
        return ""
    with translation.override(prospect.language):
        text = _("Discover the work of %(business)s (%(activity)s) on Solange Glow: %(link)s") % {
            "business": prospect.business_name or prospect.name,
            "activity": activity(prospect) or prospect.city or "Solange Glow",
            "link": link,
        }
    return f"https://wa.me/?text={quote(text)}"


def _text(template: ProspectEmailTemplate, field: str, language: str) -> str:
    return getattr(template, f"{field}_{language}", "") or getattr(template, field)


def compose(prospect: Prospect, template: ProspectEmailTemplate) -> tuple[str, str]:
    """Subject and text of a standard e-mail for this prospect, in her language."""
    from django.template import Context, Template

    if template.needs_showcase and not prospect.pro_id:
        raise errors.ShowcaseNeeded()
    if "showcase_link" in _text(template, "body", prospect.language) and not showcase_link(
        prospect
    ):
        raise errors.ShowcaseNotOnline()
    context = Context(
        {
            "name": prospect.name.split(" ")[0],
            "business": prospect.business_name or prospect.name,
            "city": prospect.city,
            "activity": activity(prospect),
            "showcase_link": showcase_link(prospect),
            "pitch": prospect.pitch.strip(),
            "link": personal_link(prospect),
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
    if found.pro_id and found.pro.prepared_by_team:
        from apps.pros import services as pro_services

        pro_services.remove_prepared(found.pro)
    return True


def on_prepared_removed(pro) -> None:
    """« Remove my page » used on a prepared showcase: never contacted again."""
    for prospect in Prospect.objects.filter(pro=pro).exclude(status=S.DECLINED):
        prospect.status = S.DECLINED
        prospect.save(update_fields=["status", "updated_at"])
        record("backoffice.prospect_declined", prospect, actor=None)


def on_password_chosen(user) -> None:
    """They opened the link and chose their password: signed up, and the page is theirs."""
    from apps.pros.models import ProProfile

    Prospect.objects.filter(pro__user=user, status__in=[S.NEW, S.CONTACTED]).update(
        status=S.SIGNED_UP, signed_up_user=user, updated_at=timezone.now()
    )
    ProProfile.objects.filter(user=user, prepared_by_team=True).update(
        prepared_by_team=False, updated_at=timezone.now()
    )
