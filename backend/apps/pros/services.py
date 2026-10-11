"""Business rules of the pros' showcases. Views stay thin and call these functions."""

from __future__ import annotations

import datetime
import re
from urllib.parse import urlparse

from django.contrib.gis.geos import GEOSException, Point, Polygon
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.core.audit.services import record, snapshot
from apps.core.choices import Role
from apps.core.media.images import InvalidImage
from apps.core.media.services import create_asset, delete_asset
from apps.core.selectors import get_setting
from apps.notifications.services import notify

from . import errors, vault
from .models import (
    Closure,
    OpeningPeriod,
    PortfolioItem,
    ProProfile,
    ProVerification,
    Service,
    ServiceCategory,
    ServiceOption,
    ServicePhoto,
    ServiceStep,
    SocialNetwork,
    SpokenLanguage,
    Trade,
)
from .search import refresh_search

SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,38}[a-z0-9])$")
# Paths of the web app and words that must never become a pro's short link.
RESERVED_SLUGS = {
    "fr", "en", "sk", "api", "admin", "s3", "static", "media", "auth", "welcome", "me",
    "explore", "create", "messages", "notifications", "design", "pro", "pros", "shop",
    "boutique", "academy", "academie", "selection", "booking", "rdv", "help", "aide",
    "support", "legal", "cgu", "cgv", "privacy", "login", "signup", "settings", "search",
    "solange", "solangeglow", "sw", "manifest", "robots", "sitemap", "favicon", "offline",
}  # fmt: skip

MEDIA_FIELDS = {
    "photo": "pro_photo",
    "cover": "pro_cover",
    "bio_voice": "pro_voice",
    "landmarks_voice": "pro_voice",
    "itinerary_video": "itinerary_video",
}


def _limit(key: str, default: int, pro: ProProfile | None = None) -> int:
    return int(get_setting(key, country=pro.country if pro else None, default=default))


# --- Profile -------------------------------------------------------------------------


def get_pro(user) -> ProProfile:
    pro = (
        ProProfile.objects.select_related("user", "country")
        .filter(user=user, user__is_active=True)
        .first()
    )
    if pro is None:
        raise errors.NotAPro()
    return pro


def check_slug(slug: str, *, pro: ProProfile | None = None) -> str:
    slug = (slug or "").strip().lower()
    if not SLUG_RE.match(slug) or "--" in slug or slug in RESERVED_SLUGS:
        raise errors.SlugInvalid()
    taken = ProProfile.objects.filter(slug=slug)
    if pro is not None:
        taken = taken.exclude(pk=pro.pk)
    if taken.exists():
        raise errors.SlugTaken()
    return slug


def suggest_slug(name: str, *, pro: ProProfile | None = None) -> str:
    base = slugify(name)[:34].strip("-") or "pro"
    if len(base) < 3:
        base = f"{base}-pro"
    candidate = base
    for number in range(2, 200):
        try:
            return check_slug(candidate, pro=pro)
        except (errors.SlugInvalid, errors.SlugTaken):
            candidate = f"{base}-{number}"
    return f"{base}-{timezone.now():%H%M%S}"


@transaction.atomic
def become_pro(
    user,
    *,
    business_name: str,
    kind: str = ProProfile.Kind.INDEPENDENT,
    trade_keys: list[str] | None = None,
    city: str = "",
    district: str = "",
) -> ProProfile:
    """First step of « Become a pro »: a draft showcase, nothing public yet."""
    pro, created = ProProfile.objects.get_or_create(user=user)
    if Role.PRO not in user.roles:
        user.roles = [*user.roles, Role.PRO]
        user.save(update_fields=["roles", "updated_at"])
    pro.business_name = business_name.strip()[:80]
    pro.kind = kind if kind in ProProfile.Kind.values else ProProfile.Kind.INDEPENDENT
    if user.country_id and not pro.country_id:
        pro.country = user.country
    if pro.country_id and not pro.currency:
        pro.currency = pro.country.default_currency.code
    pro.city = (city or pro.city or user.city).strip()[:80]
    pro.district = (district or pro.district).strip()[:80]
    if not pro.slug:
        pro.slug = suggest_slug(pro.business_name or user.first_name, pro=pro)
    pro.save()
    if trade_keys is not None:
        pro.trades.set(Trade.objects.filter(is_active=True, key__in=trade_keys))
    refresh_search(pro)
    record("pros.created" if created else "pros.started", pro, actor=user, after=snapshot(pro))
    return pro


def _clean_social_links(links: dict) -> dict:
    cleaned = {}
    for network, value in (links or {}).items():
        value = str(value or "").strip()
        if not value:
            continue
        if network not in SocialNetwork.values or len(value) > 200:
            raise errors.InvalidSocialLink()
        if network == SocialNetwork.WHATSAPP:
            digits = re.sub(r"[^\d+]", "", value)
            if not re.fullmatch(r"\+?\d{8,15}", digits):
                raise errors.InvalidSocialLink()
            value = digits
        elif value.startswith("http"):
            parsed = urlparse(value)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise errors.InvalidSocialLink()
        elif network == SocialNetwork.WEBSITE:
            raise errors.InvalidSocialLink()
        else:
            value = "@" + value.lstrip("@")
            if not re.fullmatch(r"@[\w.\-]{1,60}", value):
                raise errors.InvalidSocialLink()
        cleaned[network] = value
    return cleaned


EDITABLE = {
    "business_name",
    "kind",
    "bio",
    "city",
    "district",
    "address",
    "landmarks",
    "receives_clients",
}


@transaction.atomic
def update_profile(pro: ProProfile, *, actor, **changes) -> ProProfile:
    """Text fields of the showcase. Only the given fields change."""
    before = snapshot(pro)
    for field in EDITABLE & changes.keys():
        value = changes[field]
        if isinstance(value, str):
            value = value.strip()
        setattr(pro, field, value)
    if "slug" in changes and changes["slug"] != pro.slug:
        pro.slug = check_slug(changes["slug"], pro=pro)
    if "social_links" in changes:
        pro.social_links = _clean_social_links(changes["social_links"])
    if "languages" in changes:
        pro.languages = [c for c in dict.fromkeys(changes["languages"]) if c in SpokenLanguage]
    if not pro.business_name:
        pro.business_name = pro.user.first_name
    pro.full_clean(exclude=["user", "slug", "location", "service_area", "country"])
    pro.save()
    if "trade_keys" in changes:
        pro.trades.set(Trade.objects.filter(is_active=True, key__in=changes["trade_keys"]))
    refresh_search(pro)
    record("pros.updated", pro, actor=actor, before=before, after=snapshot(pro))
    return pro


def set_media(pro: ProProfile, field: str, uploaded) -> ProProfile:
    """New photo, cover, voice note or itinerary video, processed in the background."""
    purpose = MEDIA_FIELDS[field]
    previous = getattr(pro, field)
    asset = create_asset(owner=pro.user, uploaded=uploaded, purpose=purpose)
    setattr(pro, field, asset)
    pro.save(update_fields=[field, "updated_at"])
    if previous is not None:
        transaction.on_commit(lambda: delete_asset(previous))
    return pro


def clear_media(pro: ProProfile, field: str) -> ProProfile:
    previous = getattr(pro, field)
    if previous is not None:
        setattr(pro, field, None)
        pro.save(update_fields=[field, "updated_at"])
        transaction.on_commit(lambda: delete_asset(previous))
    return pro


def set_location(
    pro: ProProfile, *, latitude: float, longitude: float, source: str, actor
) -> ProProfile:
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise errors.InvalidLocation()
    before = snapshot(pro)
    pro.location = Point(longitude, latitude, srid=4326)
    pro.location_source = (
        source if source in ProProfile.LocationSource.values else ProProfile.LocationSource.MAP
    )
    pro.save(update_fields=["location", "location_source", "updated_at"])
    record("pros.location_changed", pro, actor=actor, before=before, after=snapshot(pro))
    return pro


def _polygon(points: list) -> Polygon:
    try:
        ring = [(float(lng), float(lat)) for lng, lat in points]
    except (TypeError, ValueError) as exc:
        raise errors.InvalidArea() from exc
    if len(ring) < 3:
        raise errors.InvalidArea()
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    try:
        polygon = Polygon(ring, srid=4326)
    except (GEOSException, ValueError, TypeError) as exc:
        raise errors.InvalidArea() from exc
    if not polygon.valid:
        raise errors.InvalidArea()
    return polygon


def set_travel(
    pro: ProProfile,
    *,
    travels: bool,
    radius_km: int | None = None,
    area: list | None = None,
    fee_minor: int | None = None,
    actor,
) -> ProProfile:
    """Home visits: a radius around her position, or an area drawn on the map, and a fee."""
    before = snapshot(pro)
    pro.travels_to_clients = travels
    if travels:
        maximum = _limit("pros.service_area_max_radius_km", 30, pro)
        if area:
            if len(area) > _limit("pros.area_max_points", 50, pro):
                raise errors.InvalidArea()
            pro.service_area = _polygon(area)
            pro.service_radius_km = None
        else:
            radius = int(radius_km or 0)
            if radius < 1:
                raise errors.InvalidArea()
            if radius > maximum:
                raise errors.RadiusTooLarge(errors.RadiusTooLarge.message % {"km": maximum})
            pro.service_radius_km = radius
            pro.service_area = None
        if fee_minor is not None and fee_minor < 0:
            raise errors.InvalidPrice()
        pro.travel_fee_minor = fee_minor
    pro.save()
    refresh_search(pro)
    record("pros.travel_changed", pro, actor=actor, before=before, after=snapshot(pro))
    return pro


# --- Publication -----------------------------------------------------------------------


def missing_for_publication(pro: ProProfile) -> list[str]:
    """What still lacks before the showcase can be published (codes, shown as a checklist)."""
    missing = []
    if not pro.business_name:
        missing.append("business_name")
    if not pro.slug:
        missing.append("slug")
    if not pro.trades.exists():
        missing.append("trades")
    if not pro.city:
        missing.append("city")
    if pro.location is None:
        missing.append("location")
    if not pro.services.filter(is_active=True, archived_at__isnull=True).exists():
        missing.append("services")
    if not pro.receives_clients and not pro.travels_to_clients:
        missing.append("where")
    return missing


def publish(pro: ProProfile, *, actor) -> ProProfile:
    if pro.status == ProProfile.Status.SUSPENDED:
        raise errors.Suspended()
    missing = missing_for_publication(pro)
    if missing:
        raise errors.NotReadyToPublish(details={"missing": missing})
    first_time = pro.published_at is None
    pro.status = ProProfile.Status.PUBLISHED
    pro.published_at = pro.published_at or timezone.now()
    pro.save(update_fields=["status", "published_at", "updated_at"])
    record("pros.published", pro, actor=actor)
    if first_time:
        notify(pro.user, "pros.published", {"link": short_link(pro)}, link=f"/{pro.slug}")
    return pro


def unpublish(pro: ProProfile, *, actor) -> ProProfile:
    if pro.status == ProProfile.Status.SUSPENDED:
        raise errors.Suspended()
    pro.status = ProProfile.Status.DRAFT
    pro.save(update_fields=["status", "updated_at"])
    record("pros.unpublished", pro, actor=actor)
    return pro


def suspend(pro: ProProfile, *, actor, reason: str) -> ProProfile:
    before = snapshot(pro)
    pro.status = ProProfile.Status.SUSPENDED
    pro.suspended_at = timezone.now()
    pro.suspension_reason = reason.strip()
    pro.save(update_fields=["status", "suspended_at", "suspension_reason", "updated_at"])
    record("pros.suspended", pro, actor=actor, before=before, after=snapshot(pro))
    notify(pro.user, "pros.suspended", {"reason": pro.suspension_reason})
    return pro


def reinstate(pro: ProProfile, *, actor) -> ProProfile:
    """End of a suspension: back online if it was published before, else draft."""
    before = snapshot(pro)
    pro.status = ProProfile.Status.PUBLISHED if pro.published_at else ProProfile.Status.DRAFT
    pro.suspended_at = None
    pro.suspension_reason = ""
    pro.save(update_fields=["status", "suspended_at", "suspension_reason", "updated_at"])
    record("pros.reinstated", pro, actor=actor, before=before, after=snapshot(pro))
    return pro


def short_link(pro: ProProfile) -> str:
    from django.conf import settings

    return f"{settings.SHORT_LINK_BASE_URL.rstrip('/')}/{pro.slug}"


# --- Services --------------------------------------------------------------------------


def _clean_steps(steps: list[dict]) -> list[dict]:
    cleaned = []
    for step in steps or []:
        minutes = int(step.get("duration_minutes") or 0)
        if minutes < 1 or minutes > 24 * 60:
            raise errors.InvalidDuration()
        kind = step.get("kind") or ServiceStep.Kind.WORK
        if kind not in ServiceStep.Kind.values:
            raise errors.InvalidDuration()
        cleaned.append(
            {
                "kind": kind,
                "label": str(step.get("label") or "").strip()[:60],
                "duration_minutes": minutes,
                "needs_staff": kind == ServiceStep.Kind.WORK,
            }
        )
    if not any(s["kind"] == ServiceStep.Kind.WORK for s in cleaned):
        raise errors.InvalidDuration()
    return cleaned


@transaction.atomic
def save_service(pro: ProProfile, data: dict, *, service: Service | None = None) -> Service:
    """Creates or replaces a service with its steps and options."""
    if service is None:
        maximum = _limit("pros.max_services", 100, pro)
        if pro.services.filter(archived_at__isnull=True).count() >= maximum:
            raise errors.TooMany(errors.TooMany.message % {"limit": maximum})
        service = Service(pro=pro, currency=pro.currency or "XOF")

    price_kind = data.get("price_kind", service.price_kind)
    price = data.get("price_minor", service.price_minor)
    if price_kind not in Service.PriceKind.values:
        raise errors.InvalidPrice()
    if price_kind == Service.PriceKind.QUOTE:
        price = None
    elif price is None or int(price) < 0:
        raise errors.InvalidPrice()

    category_id = data.get("category_id", service.category_id)
    category = pro.categories.filter(pk=category_id).first() if category_id else None
    trade_key = data.get("trade_key")
    if trade_key is not None:
        service.trade = Trade.objects.filter(key=trade_key, is_active=True).first()

    service.name = str(data.get("name", service.name) or "").strip()[:80]
    if not service.name:
        raise errors.NameRequired()
    service.description = str(data.get("description", service.description) or "").strip()
    service.price_kind = price_kind
    service.price_minor = None if price is None else int(price)
    service.category = category
    service.available_at_home = bool(data.get("available_at_home", service.available_at_home))
    service.is_active = bool(data.get("is_active", service.is_active))
    if "position" in data:
        service.position = int(data["position"] or 0)

    steps = data.get("steps")
    if steps is not None:
        steps = _clean_steps(steps)
        service.duration_minutes = sum(s["duration_minutes"] for s in steps)
    elif service._state.adding:
        raise errors.InvalidDuration()
    service.full_clean(exclude=["pro", "category", "trade"])
    service.save()

    if steps is not None:
        service.steps.all().delete()
        ServiceStep.objects.bulk_create(
            ServiceStep(service=service, position=index, **step) for index, step in enumerate(steps)
        )
    options = data.get("options")
    if options is not None:
        maximum = _limit("pros.max_options_per_service", 10, pro)
        if len(options) > maximum:
            raise errors.TooMany(errors.TooMany.message % {"limit": maximum})
        service.options.all().delete()
        for index, option in enumerate(options):
            name = str(option.get("name") or "").strip()[:80]
            option_price = int(option.get("price_minor") or 0)
            extra = int(option.get("extra_minutes") or 0)
            if not name or option_price < 0 or extra < 0:
                raise errors.InvalidPrice()
            ServiceOption.objects.create(
                service=service,
                name=name,
                price_minor=option_price,
                extra_minutes=extra,
                position=index,
            )
    refresh_search(pro)
    return service


def archive_service(service: Service) -> None:
    """Kept for the history of bookings; hidden everywhere."""
    service.is_active = False
    service.archived_at = timezone.now()
    service.save(update_fields=["is_active", "archived_at", "updated_at"])
    refresh_search(service.pro)


def add_service_photo(service: Service, uploaded) -> ServicePhoto:
    maximum = _limit("pros.max_service_photos", 6, service.pro)
    if service.photos.count() >= maximum:
        raise errors.TooMany(errors.TooMany.message % {"limit": maximum})
    asset = create_asset(owner=service.pro.user, uploaded=uploaded, purpose="service_photo")
    return ServicePhoto.objects.create(
        service=service, media=asset, position=service.photos.count()
    )


def remove_service_photo(photo: ServicePhoto) -> None:
    asset = photo.media
    photo.delete()
    transaction.on_commit(lambda: delete_asset(asset))


def save_category(
    pro: ProProfile, *, name: str, position: int = 0, category: ServiceCategory | None = None
) -> ServiceCategory:
    if category is None:
        maximum = _limit("pros.max_categories", 20, pro)
        if pro.categories.count() >= maximum:
            raise errors.TooMany(errors.TooMany.message % {"limit": maximum})
        category = ServiceCategory(pro=pro)
    category.name = name.strip()[:60]
    category.position = position
    category.full_clean(exclude=["pro"])
    category.save()
    refresh_search(pro)
    return category


def delete_category(category: ServiceCategory) -> None:
    pro = category.pro
    category.delete()  # its services stay, without category
    refresh_search(pro)


# --- Hours -----------------------------------------------------------------------------


@transaction.atomic
def set_opening_hours(pro: ProProfile, periods: list[dict]) -> list[OpeningPeriod]:
    """Replaces the whole week. Several periods on a day leave breaks between them."""
    by_day: dict[int, list[tuple[datetime.time, datetime.time]]] = {}
    for period in periods:
        weekday = int(period["weekday"])
        opens, closes = period["opens_at"], period["closes_at"]
        if not 0 <= weekday <= 6:
            raise errors.InvalidHours(errors.InvalidHours.message % {"day": weekday})
        by_day.setdefault(weekday, []).append((opens, closes))
    for weekday, spans in by_day.items():
        spans.sort()
        day = str(OpeningPeriod.Weekday(weekday).label)
        for index, (opens, closes) in enumerate(spans):
            if closes <= opens or (index and opens < spans[index - 1][1]):
                raise errors.InvalidHours(errors.InvalidHours.message % {"day": day})
    pro.opening_periods.all().delete()
    created = OpeningPeriod.objects.bulk_create(
        OpeningPeriod(pro=pro, weekday=weekday, opens_at=opens, closes_at=closes)
        for weekday, spans in sorted(by_day.items())
        for opens, closes in spans
    )
    return created


def add_closure(
    pro: ProProfile, *, starts_on: datetime.date, ends_on: datetime.date, reason: str = ""
) -> Closure:
    if ends_on < starts_on:
        raise errors.InvalidClosure()
    return Closure.objects.create(
        pro=pro, starts_on=starts_on, ends_on=ends_on, reason=reason.strip()[:120]
    )


# --- Portfolio -------------------------------------------------------------------------


def add_portfolio_item(
    pro: ProProfile,
    *,
    uploaded,
    before=None,
    caption: str = "",
    service: Service | None = None,
) -> PortfolioItem:
    maximum = _limit("pros.max_portfolio_items", 60, pro)
    if pro.portfolio.count() >= maximum:
        raise errors.TooMany(errors.TooMany.message % {"limit": maximum})
    media = create_asset(owner=pro.user, uploaded=uploaded, purpose="portfolio")
    before_media = (
        create_asset(owner=pro.user, uploaded=before, purpose="portfolio", kind="image")
        if before is not None
        else None
    )
    first = pro.portfolio.order_by("position").values_list("position", flat=True).first()
    return PortfolioItem.objects.create(
        pro=pro,
        media=media,
        before_media=before_media,
        caption=caption.strip()[:200],
        service=service if service is None or service.pro_id == pro.pk else None,
        position=max((first or 0) - 1, 0),
    )


def update_portfolio_item(item: PortfolioItem, **changes) -> PortfolioItem:
    if "caption" in changes:
        item.caption = str(changes["caption"] or "").strip()[:200]
    if "service_id" in changes:
        service_id = changes["service_id"]
        item.service = item.pro.services.filter(pk=service_id).first() if service_id else None
    if "position" in changes:
        item.position = max(int(changes["position"] or 0), 0)
    item.save()
    return item


def delete_portfolio_item(item: PortfolioItem) -> None:
    assets = [a for a in (item.media, item.before_media) if a is not None]
    item.delete()
    transaction.on_commit(lambda: [delete_asset(a) for a in assets])


# --- Verification ----------------------------------------------------------------------


@transaction.atomic
def submit_verification(
    pro: ProProfile, *, document, selfie, document_type: str
) -> ProVerification:
    """Identity document + selfie: cleaned, encrypted, queued for the verification team."""
    if pro.verification_status == ProProfile.Verification.VERIFIED:
        raise errors.AlreadyVerified()
    if pro.verifications.filter(status=ProVerification.Status.PENDING).exists():
        raise errors.VerificationAlreadySent()
    try:
        sealed_document = vault.seal_image(document)
        sealed_selfie = vault.seal_image(selfie)
    except InvalidImage as exc:
        raise errors.MediaNotReady() from exc
    verification = ProVerification(
        pro=pro,
        document_type=(
            document_type
            if document_type in ProVerification.DocumentType.values
            else ProVerification.DocumentType.ID_CARD
        ),
    )
    verification.document_file.save("document.bin", sealed_document, save=False)
    verification.selfie_file.save("selfie.bin", sealed_selfie, save=False)
    verification.save()
    pro.verification_status = ProProfile.Verification.PENDING
    pro.save(update_fields=["verification_status", "updated_at"])
    record("pros.verification_submitted", verification, actor=pro.user)
    return verification


@transaction.atomic
def review_verification(
    verification: ProVerification, *, actor, approve: bool, reason: str = ""
) -> ProVerification:
    pro = verification.pro
    verification.status = (
        ProVerification.Status.APPROVED if approve else ProVerification.Status.REJECTED
    )
    verification.reviewed_by = actor
    verification.reviewed_at = timezone.now()
    verification.rejection_reason = "" if approve else reason.strip()
    verification.save()
    if approve:
        pro.verification_status = ProProfile.Verification.VERIFIED
        pro.verified_at = verification.reviewed_at
    else:
        pro.verification_status = ProProfile.Verification.REJECTED
    pro.save(update_fields=["verification_status", "verified_at", "updated_at"])
    record(
        "pros.verification_approved" if approve else "pros.verification_rejected",
        verification,
        actor=actor,
        metadata={"reason": verification.rejection_reason},
    )
    if approve:
        notify(pro.user, "pros.verification_approved")
    else:
        notify(pro.user, "pros.verification_rejected", {"reason": verification.rejection_reason})
    return verification


def read_verification_file(verification: ProVerification, which: str, *, actor) -> bytes:
    """Decrypted picture for the verification team. Every reading is in the audit journal."""
    field = verification.document_file if which == "document" else verification.selfie_file
    data = vault.open_sealed(field)
    record("pros.identity_viewed", verification, actor=actor, metadata={"file": which})
    return data


# --- « I am outside » ------------------------------------------------------------------


def announce_arrival(pro: ProProfile, *, user=None, guest_name: str = "", guest_key: str = ""):
    """The client is at the door: the pro gets an alert right away."""
    if not pro.is_published:
        raise errors.ProNotFound()
    if not pro.receives_clients:
        raise errors.ArrivalNotPossible()
    who = user.pk if user is not None else guest_key
    if not who:
        raise errors.IdentityRequired()
    minutes = _limit("pros.arrival_cooldown_minutes", 5, pro)
    if not cache.add(f"pros:arrival:{pro.pk}:{who}", 1, timeout=minutes * 60):
        raise errors.ArrivalTooSoon()
    name = (user.first_name if user is not None else guest_name).strip() or "?"
    notify(pro.user, "pros.client_arrived", {"name": name})
