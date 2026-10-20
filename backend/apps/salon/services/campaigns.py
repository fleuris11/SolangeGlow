"""Marketing consents and campaigns (Premium).

Only clients who said yes on a channel receive a campaign on it; each message carries a
link to say no. Segments: not come for a while, birthday soon, package almost used, all.
"""

from __future__ import annotations

import datetime

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.db.models import Max, Q
from django.template import engines
from django.utils import timezone

from apps.booking.models import Appointment, ClientRecord
from apps.core.audit.services import record
from apps.glowpro import selectors as glowpro
from apps.glowpro.models import Feature
from apps.notifications.services import send_direct

from .. import errors
from ..models import Campaign, CampaignMessage, ClientPackage, MarketingConsent
from . import common

SALT = "salon.unsubscribe"
Seg = Campaign.Segment
A = Appointment.Status


# --- Consents -----------------------------------------------------------------------------------


def set_consent(client_record: ClientRecord, channel: str, granted: bool, *, source: str):
    consent, _ = MarketingConsent.objects.update_or_create(
        record=client_record,
        channel=channel,
        defaults={"granted": bool(granted), "source": source, "changed_at": timezone.now()},
    )
    record("salon.consent", client_record, metadata={"channel": channel, "granted": granted})
    return consent


def consents_of(client_record: ClientRecord) -> dict[str, bool]:
    return {c.channel: c.granted for c in client_record.consents.all()}


def unsubscribe_token(client_record: ClientRecord, channel: str) -> str:
    return signing.dumps({"r": str(client_record.pk), "c": channel}, salt=SALT, compress=True)


def unsubscribe_url(client_record: ClientRecord, channel: str) -> str:
    return (
        f"{settings.SITE_URL.rstrip('/')}/desabonnement/{unsubscribe_token(client_record, channel)}"
    )


def read_token(token: str) -> tuple[ClientRecord, str]:
    try:
        data = signing.loads(token, salt=SALT)
    except signing.BadSignature as exc:
        raise errors.InvalidUnsubscribe() from exc
    found = ClientRecord.objects.select_related("pro").filter(pk=data.get("r")).first()
    if found is None or data.get("c") not in ("email", "whatsapp"):
        raise errors.InvalidUnsubscribe()
    return found, data["c"]


def unsubscribe(token: str) -> tuple[ClientRecord, str]:
    found, channel = read_token(token)
    set_consent(found, channel, False, source=MarketingConsent.Source.UNSUBSCRIBE)
    return found, channel


# --- Segments -----------------------------------------------------------------------------------


def segment(pro, kind: str, *, inactive_days: int = 60, today=None):
    """Client files of the segment (before consents)."""
    today = today or timezone.localdate()
    rows = ClientRecord.objects.filter(pro=pro).select_related("client")
    if kind == Seg.INACTIVE:
        limit = timezone.now() - datetime.timedelta(days=inactive_days)
        last = {}
        for row in (
            Appointment.objects.filter(pro=pro, status=A.COMPLETED)
            .values("client_id", "client_phone")
            .annotate(last=Max("starts_at"))
        ):
            if row["client_id"]:
                last[("c", row["client_id"])] = max(
                    row["last"], last.get(("c", row["client_id"]), row["last"])
                )
            if row["client_phone"]:
                last[("p", row["client_phone"])] = max(
                    row["last"], last.get(("p", row["client_phone"]), row["last"])
                )
        upcoming = Appointment.objects.filter(
            pro=pro, status__in=Appointment.BLOCKING, starts_at__gte=timezone.now()
        )
        coming_clients = set(upcoming.values_list("client_id", flat=True))
        coming_phones = set(upcoming.values_list("client_phone", flat=True))
        chosen = []
        for item in rows:
            seen = (
                last.get(("c", item.client_id)) if item.client_id else last.get(("p", item.phone))
            )
            if seen is None or seen > limit:
                continue
            if item.client_id in coming_clients or (item.phone and item.phone in coming_phones):
                continue
            chosen.append(item.pk)
        return rows.filter(pk__in=chosen)
    if kind == Seg.BIRTHDAY:
        days = [today + datetime.timedelta(days=i) for i in range(8)]
        chosen = [
            item.pk
            for item in rows
            if (found := common.birthday(item)) and any((d.day, d.month) == found for d in days)
        ]
        return rows.filter(pk__in=chosen)
    if kind == Seg.PACKAGE_LOW:
        ids = [
            p.record_id
            for p in ClientPackage.objects.filter(pro=pro, status=ClientPackage.Status.ACTIVE)
            if p.sessions_left <= 1
        ]
        return rows.filter(pk__in=ids)
    return rows


def audience(campaign: Campaign) -> tuple[list[tuple[ClientRecord, str]], int]:
    """(file, destination) of who will receive it, and how many are left out (no consent)."""
    rows = segment(campaign.pro, campaign.segment, inactive_days=campaign.inactive_days)
    agreed = set(
        MarketingConsent.objects.filter(
            record__in=rows, channel=campaign.channel, granted=True
        ).values_list("record_id", flat=True)
    )
    chosen, left_out = [], 0
    for item in rows:
        where = common.destination(item, campaign.channel)
        if item.pk not in agreed or not where:
            left_out += 1
            continue
        chosen.append((item, where))
    return chosen, left_out


# --- Campaigns ----------------------------------------------------------------------------------


@transaction.atomic
def save_campaign(pro, *, campaign_id=None, **values) -> Campaign:
    glowpro.require(pro, Feature.CAMPAIGNS)
    name = (values.get("name") or "").strip()[:80]
    body = (values.get("body") or "").strip()[:1000]
    channel = values.get("channel")
    subject = (values.get("subject") or "").strip()[:120]
    if (
        not name
        or not body
        or channel not in ("email", "whatsapp")
        or values.get("segment") not in Seg.values
        or (channel == "email" and not subject)
    ):
        raise errors.InvalidCampaign()
    campaign = (
        Campaign.objects.filter(pk=campaign_id, pro=pro).first()
        if campaign_id
        else Campaign(pro=pro)
    )
    if campaign is None:
        raise errors.NotFound()
    if campaign.status == Campaign.Status.SENT:
        raise errors.CampaignSent()
    campaign.name, campaign.body, campaign.subject = name, body, subject
    campaign.channel, campaign.segment = channel, values["segment"]
    campaign.inactive_days = int(values.get("inactive_days") or 60)
    campaign.save()
    return campaign


def _render(text: str, context: dict) -> str:
    template = engines["django"].from_string("{% autoescape off %}" + text + "{% endautoescape %}")
    return template.render(context).strip()


@transaction.atomic
def send(campaign: Campaign, *, actor=None) -> Campaign:
    campaign = Campaign.objects.select_for_update().select_related("pro").get(pk=campaign.pk)
    pro = campaign.pro
    glowpro.require(pro, Feature.CAMPAIGNS)
    if campaign.status == Campaign.Status.SENT:
        raise errors.CampaignSent()
    limit = glowpro.limit(pro, "campaigns_per_month")
    if limit is not None:
        start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if Campaign.objects.filter(pro=pro, status="sent", sent_at__gte=start).count() >= limit:
            raise errors.CampaignLimit(details={"limit": limit})
    chosen, left_out = audience(campaign)
    CampaignMessage.objects.bulk_create(
        CampaignMessage(campaign=campaign, record=item, destination=where) for item, where in chosen
    )
    campaign.status = Campaign.Status.SENT
    campaign.sent_at = timezone.now()
    campaign.targeted = len(chosen) + left_out
    campaign.without_consent = left_out
    campaign.save()
    record("salon.campaign_sent", campaign, actor=actor, metadata={"to": len(chosen)})

    def deliver():
        from ..tasks import deliver_campaign

        deliver_campaign.delay(str(campaign.pk))

    transaction.on_commit(deliver)
    return campaign


def deliver(campaign_id) -> int:
    """Sends the waiting messages of a campaign (Celery)."""
    campaign = Campaign.objects.select_related("pro").get(pk=campaign_id)
    sent = 0
    for message in CampaignMessage.objects.filter(
        campaign=campaign, status=CampaignMessage.Status.PENDING
    ).select_related("record__client"):
        context = {
            "first_name": common.first_name(message.record),
            "pro": campaign.pro.display_name,
        }
        error = send_direct(
            campaign.channel,
            message.destination,
            _render(campaign.subject, context),
            _render(campaign.body, context),
            unsubscribe_url=unsubscribe_url(message.record, campaign.channel),
        )
        message.status = CampaignMessage.Status.FAILED if error else CampaignMessage.Status.SENT
        message.error = error[:200]
        message.sent_at = None if error else timezone.now()
        message.save(update_fields=["status", "error", "sent_at", "updated_at"])
        sent += not error
    return sent


def stats(campaign: Campaign) -> dict:
    messages = CampaignMessage.objects.filter(campaign=campaign)
    counts = dict.fromkeys(CampaignMessage.Status.values, 0)
    for status in messages.values_list("status", flat=True):
        counts[status] += 1
    record_ids = list(messages.values_list("record_id", flat=True))
    unsubscribed = 0
    returned = 0
    if campaign.sent_at and record_ids:
        unsubscribed = MarketingConsent.objects.filter(
            record_id__in=record_ids,
            channel=campaign.channel,
            granted=False,
            changed_at__gte=campaign.sent_at,
        ).count()
        files = ClientRecord.objects.filter(pk__in=record_ids)
        clients = [f.client_id for f in files if f.client_id]
        phones = [f.phone for f in files if f.phone]
        window = campaign.sent_at + datetime.timedelta(days=30)
        returned = (
            Appointment.objects.filter(
                Q(client_id__in=clients) | Q(client_phone__in=phones),
                pro=campaign.pro,
                created_at__gte=campaign.sent_at,
                created_at__lte=window,
            )
            .values("client_id", "client_phone")
            .distinct()
            .count()
        )
    return {
        "targeted": campaign.targeted,
        "without_consent": campaign.without_consent,
        "pending": counts["pending"],
        "sent": counts["sent"],
        "failed": counts["failed"],
        "unsubscribed": unsubscribed,
        "returned": returned,
    }
