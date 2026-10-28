"""Proof of joy: after the offered service, a photo of the result goes to the person who
offered it, only when the person who received the gift says yes."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.core.audit.services import record
from apps.core.media import services as media_services
from apps.core.media.models import MediaAsset
from apps.notifications.services import notify

from .. import errors
from ..models import Gift, GiftPhoto, GiftUse
from . import common, offering
from .using import is_giver

G = Gift.Status


def candidates(gift: Gift) -> list[tuple[MediaAsset, str]]:
    """Photos the person may send: the pro's pictures of the result, and her own."""
    from apps.booking.models import AppointmentPhoto

    found: list[tuple[MediaAsset, str]] = []
    appointments = GiftUse.objects.filter(gift=gift, source_type="booking").values_list(
        "source_id", flat=True
    )
    for photo in AppointmentPhoto.objects.filter(
        appointment_id__in=list(appointments)
    ).select_related("media"):
        found.append((photo.media, GiftPhoto.Source.PRO))
    for photo in gift.photos.select_related("media"):
        found.append((photo.media, photo.source))
    return [(media, source) for media, source in found if media.is_ready]


def _check_recipient(gift: Gift, viewer) -> None:
    if is_giver(gift, viewer):
        raise errors.GiverCannotDoThis()
    if gift.status not in (G.USED, G.OPENED, G.SENT):
        raise errors.WrongKind()


def add_photo(gift: Gift, uploaded, *, viewer=None) -> GiftPhoto:
    """Her own photo (with or without an account): it waits for her « yes »."""
    _check_recipient(gift, viewer)
    owner = viewer if viewer is not None and viewer.is_authenticated else None
    asset = media_services.create_asset(owner=owner, uploaded=uploaded, purpose="gift_proof")
    return GiftPhoto.objects.create(gift=gift, media=asset, source=GiftPhoto.Source.RECIPIENT)


@transaction.atomic
def answer(gift: Gift, media_id, *, send: bool, viewer=None) -> Gift:
    """« Send this photo to Awa? » Yes: she receives it. No: nothing leaves."""
    _check_recipient(gift, viewer)
    gift = common.locked(gift)
    if not send:
        gift.proof_status = Gift.Proof.DECLINED
        gift.save(update_fields=["proof_status", "updated_at"])
        record("gifts.proof_declined", gift)
        return gift
    media = next((m for m, _source in candidates(gift) if str(m.pk) == str(media_id)), None)
    if media is None:
        raise errors.PhotoNotFound()
    gift.proof_media = media
    gift.proof_status = Gift.Proof.SENT
    gift.proof_sent_at = timezone.now()
    gift.save(update_fields=["proof_media", "proof_status", "proof_sent_at", "updated_at"])
    record("gifts.proof_sent", gift)
    common.after_commit(
        lambda: notify(
            gift.giver,
            "gifts.proof",
            {"name": gift.recipient_name, "what": gift.title},
            link=f"/cadeaux/{gift.pk}",
        )
    )
    return gift


def on_completed(appointment) -> None:
    """The offered service is done: the person is asked whether a photo may go (once)."""
    use = (
        GiftUse.objects.select_related("gift")
        .filter(source_type="booking", source_id=appointment.pk)
        .first()
    )
    if use is None:
        return
    gift = use.gift
    if gift.proof_asked_at or gift.proof_status:
        return
    Gift.objects.filter(pk=gift.pk).update(proof_asked_at=timezone.now())
    common.after_commit(lambda: offering.deliver(gift, "gifts.proof_ask"))
