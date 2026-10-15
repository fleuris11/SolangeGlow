"""A pro's shop: her products (photos, variants, stock), publication with the forbidden
words check, the review by the team, and how she hands over her orders."""

from __future__ import annotations

import uuid

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.core.audit.services import record
from apps.core.media.models import MediaAsset
from apps.core.media.services import variant_url
from apps.core.selectors import get_setting
from apps.moderation.services import screen
from apps.notifications.services import notify
from apps.pros.models import ProProfile
from apps.pros.selectors import can_collect_payments

from .. import errors, forbidden
from ..models import (
    CartItem,
    Category,
    DeliveryZone,
    Product,
    ProductPhoto,
    ShopProfile,
    Variant,
)
from ..selectors import shop_enabled, shop_of

P = Product.Status


def pro_of(user) -> ProProfile:
    try:
        return user.pro_profile
    except (ObjectDoesNotExist, AttributeError) as exc:
        raise errors.NotAPro() from exc


def _setting(key: str, pro: ProProfile, default):
    return get_setting(key, country=pro.country, default=default)


def _language(user) -> str:
    return getattr(user, "preferred_language", "") or "fr"


def _unique_slug(pro: ProProfile, title: str, exclude=None) -> str:
    base = slugify(title)[:120].strip("-") or "produit"
    taken = set(
        Product.objects.filter(pro=pro, slug__startswith=base)
        .exclude(pk=exclude)
        .values_list("slug", flat=True)
    )
    slug, number = base, 2
    while slug in taken:
        slug = f"{base}-{number}"
        number += 1
    return slug


def _media(user, media_id, purpose: str) -> MediaAsset | None:
    if not media_id:
        return None
    asset = MediaAsset.objects.filter(pk=media_id, owner=user, purpose=purpose).first()
    if asset is None or asset.status in (MediaAsset.Status.REJECTED, MediaAsset.Status.FAILED):
        raise errors.InvalidMedia()
    return asset


def _amount(value, *, allow_none: bool = False, minimum: int = 1):
    if value is None and allow_none:
        return None
    if type(value) is not int or value < minimum:
        raise errors.InvalidVariants() if allow_none else errors.IncompleteProduct()
    return value


def _clean_variants(rows: list[dict]) -> list[dict]:
    """One variant without choices, or several with distinct shades, sizes or colours."""
    if not rows:
        rows = [{}]
    cleaned, seen = [], set()
    for row in rows:
        item = {
            "id": row.get("id"),
            "shade": (row.get("shade") or "").strip()[:60],
            "swatch": (row.get("swatch") or "").strip()[:7],
            "size": (row.get("size") or "").strip()[:30],
            "color": (row.get("color") or "").strip()[:40],
            "price_minor": _amount(row.get("price_minor"), allow_none=True),
            "stock": row.get("stock", 0),
        }
        if type(item["stock"]) is not int or item["stock"] < 0:
            raise errors.InvalidVariants()
        if item["swatch"] and not (
            len(item["swatch"]) == 7
            and item["swatch"][0] == "#"
            and all(c in "0123456789abcdefABCDEF" for c in item["swatch"][1:])
        ):
            raise errors.InvalidVariants()
        key = (item["shade"].lower(), item["size"].lower(), item["color"].lower())
        if (len(rows) > 1 and key == ("", "", "")) or key in seen:
            raise errors.InvalidVariants()
        seen.add(key)
        cleaned.append(item)
    return cleaned


@transaction.atomic
def save_product(
    user,
    *,
    product: Product | None = None,
    title: str,
    price_minor: int,
    category_key: str | None = None,
    description: str = "",
    prep_days: int = 1,
    photo_ids: list | None = None,
    video_id=None,
    voice_id=None,
    variants: list[dict] | None = None,
) -> Product:
    """Creates or changes a product (a draft until published). Variants are synchronised:
    a choice left out is switched off, never deleted (orders keep their history)."""
    pro = pro_of(user)
    if product is not None and (product.pro_id != pro.pk or product.status == P.ARCHIVED):
        raise errors.ProductNotFound()
    title = (title or "").strip()[:120]
    if not title:
        raise errors.IncompleteProduct()
    price_minor = _amount(price_minor)
    maximum_days = int(_setting("shop.prep_days_max", pro, 60))
    if type(prep_days) is not int or not 0 <= prep_days <= maximum_days:
        raise errors.IncompleteProduct()
    category = None
    if category_key:
        category = Category.objects.filter(key=category_key, is_active=True).first()
        if category is None:
            raise errors.IncompleteProduct()
    photo_ids = list(dict.fromkeys(photo_ids or []))
    maximum = int(_setting("shop.max_photos", pro, 8))
    if len(photo_ids) > maximum:
        raise errors.TooManyPhotos(details={"max": maximum})
    photos = [_media(user, media_id, "product_photo") for media_id in photo_ids]
    video = _media(user, video_id, "product_video")
    voice = _media(user, voice_id, "product_voice")
    rows = _clean_variants(variants or [])

    creating = product is None
    if creating:
        product = Product(pro=pro, currency=pro.currency or "XOF")
        product.slug = _unique_slug(pro, title)
    elif product.title != title:
        product.slug = _unique_slug(pro, title, exclude=product.pk)
    before_price = None if creating else product.price_minor
    product.title = title
    product.description = (description or "").strip()[:3000]
    product.price_minor = price_minor
    product.prep_days = prep_days
    product.category = category
    product.video = video
    product.description_voice = voice
    product.save()

    ProductPhoto.objects.filter(product=product).delete()
    ProductPhoto.objects.bulk_create(
        ProductPhoto(product=product, media=asset, position=index)
        for index, asset in enumerate(photos)
    )
    restocked, price_changed = _sync_variants(product, rows)
    price_changed = price_changed or (before_price is not None and before_price != price_minor)

    if product.status in (P.PUBLISHED, P.IN_REVIEW):
        _check_again(product)
    from . import alerts

    transaction.on_commit(lambda: alerts.after_change(product.pk, restocked, price_changed))
    return product


def _sync_variants(product: Product, rows: list[dict]) -> tuple[list, bool]:
    existing = {v.pk: v for v in product.variants.all()}
    kept, restocked, price_changed = set(), [], False
    for position, row in enumerate(rows):
        variant = existing.get(_uuid(row["id"])) if row["id"] else None
        if variant is None:
            variant = Variant(product=product)
        else:
            kept.add(variant.pk)
            if variant.stock == 0 and row["stock"] > 0:
                restocked.append(variant.pk)
            if variant.price_minor != row["price_minor"]:
                price_changed = True
        for field in ("shade", "swatch", "size", "color", "price_minor", "stock"):
            setattr(variant, field, row[field])
        variant.position = position
        variant.is_active = True
        variant.save()
    for pk, variant in existing.items():
        if pk not in kept and variant.is_active:
            variant.is_active = False
            variant.save(update_fields=["is_active", "updated_at"])
            CartItem.objects.filter(variant=variant).delete()
    return restocked, price_changed


def _uuid(value):
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def _image_urls(product: Product) -> list[str]:
    urls = []
    for photo in product.photos.select_related("media"):
        url = variant_url(photo.media, "medium")
        if url:
            urls.append(url)
    return urls


def _check_again(product: Product) -> None:
    """A product already online that is changed is checked again (words and moderation)."""
    finding = forbidden.check_product(product)
    if finding.blocked:
        raise errors.ForbiddenProduct(
            details={"terms": ", ".join(finding.blocked), "reasons": " ".join(finding.reasons)}
        )
    if finding.review and product.status == P.PUBLISHED:
        _to_review(product, finding)
    screen(
        product,
        text=forbidden.product_text(product),
        image_urls=_image_urls(product),
        language=_language(product.pro.user),
    )


def _to_review(product: Product, finding: forbidden.Finding) -> None:
    product.status = P.IN_REVIEW
    product.matched_terms = finding.terms
    product.review_reason = " ".join(finding.reasons)[:255] or ", ".join(finding.terms)[:255]
    product.save(update_fields=["status", "matched_terms", "review_reason", "updated_at"])
    record("shop.product_in_review", product, metadata={"terms": finding.terms})


def publish(user, product: Product) -> Product:
    """Online at once, or in the review queue (doubtful words), or refused (forbidden)."""
    pro = pro_of(user)
    if product.pro_id != pro.pk or product.status == P.ARCHIVED:
        raise errors.ProductNotFound()
    if product.status not in (P.DRAFT, P.PAUSED):
        raise errors.InvalidStep()
    if not shop_enabled(pro.country):
        raise errors.ShopUnavailable()
    if not can_collect_payments(pro):
        raise errors.VerificationNeeded()
    if (
        product.category_id is None
        or not product.photos.exists()
        or not product.variants.filter(is_active=True).exists()
    ):
        raise errors.IncompleteProduct()
    finding = forbidden.check_product(product)
    if finding.blocked:
        Product.objects.filter(pk=product.pk).update(matched_terms=finding.terms)
        record("shop.product_refused", product, actor=user, metadata={"terms": finding.terms})
        raise errors.ForbiddenProduct(
            details={"terms": ", ".join(finding.blocked), "reasons": " ".join(finding.reasons)}
        )
    with transaction.atomic():
        if finding.review:
            _to_review(product, finding)
        else:
            product.status = P.PUBLISHED
            product.published_at = product.published_at or timezone.now()
            product.matched_terms = []
            product.review_reason = ""
            product.save(
                update_fields=[
                    "status",
                    "published_at",
                    "matched_terms",
                    "review_reason",
                    "updated_at",
                ]
            )
        screen(
            product,
            text=forbidden.product_text(product),
            image_urls=_image_urls(product),
            language=_language(user),
        )
    return product


def pause(user, product: Product) -> Product:
    if product.pro_id != pro_of(user).pk:
        raise errors.ProductNotFound()
    if product.status != P.PUBLISHED:
        raise errors.InvalidStep()
    product.status = P.PAUSED
    product.save(update_fields=["status", "updated_at"])
    return product


@transaction.atomic
def archive(user, product: Product) -> None:
    """Deleted for the pro and the clients; past orders keep their copy."""
    if product.pro_id != pro_of(user).pk:
        raise errors.ProductNotFound()
    product.status = P.ARCHIVED
    product.archived_at = timezone.now()
    product.save(update_fields=["status", "archived_at", "updated_at"])
    CartItem.objects.filter(variant__product=product).delete()


@transaction.atomic
def set_stock(user, variant_id, stock: int) -> Variant:
    """Quick change of a stock from the list of « My shop »."""
    variant = (
        Variant.objects.select_for_update()
        .select_related("product")
        .filter(pk=variant_id, product__pro=pro_of(user))
        .exclude(product__status=P.ARCHIVED)
        .first()
    )
    if variant is None:
        raise errors.ProductNotFound()
    if type(stock) is not int or stock < 0:
        raise errors.InvalidVariants()
    back = variant.stock == 0 and stock > 0
    variant.stock = stock
    variant.save(update_fields=["stock", "updated_at"])
    if back:
        from . import alerts

        transaction.on_commit(lambda: alerts.after_change(variant.product_id, [variant.pk], False))
    return variant


# --- The team (admin) ----------------------------------------------------------------------------


@transaction.atomic
def approve(product: Product, *, actor) -> Product:
    if product.status != P.IN_REVIEW:
        raise errors.InvalidStep()
    product.status = P.PUBLISHED
    product.published_at = product.published_at or timezone.now()
    product.review_reason = ""
    product.save(update_fields=["status", "published_at", "review_reason", "updated_at"])
    record("shop.product_approved", product, actor=actor)
    user = product.pro.user
    transaction.on_commit(
        lambda: notify(
            user, "shop.product_approved", {"product": product.title}, link="/pro/shop/products"
        )
    )
    return product


@transaction.atomic
def refuse(product: Product, *, actor, reason: str = "") -> Product:
    """Blocked: off sale, out of every cart; only the team can put it back."""
    if product.status == P.ARCHIVED:
        raise errors.InvalidStep()
    product.status = P.BLOCKED
    product.review_reason = (reason or product.review_reason)[:255]
    product.save(update_fields=["status", "review_reason", "updated_at"])
    CartItem.objects.filter(variant__product=product).delete()
    record("shop.product_blocked", product, actor=actor, metadata={"reason": reason})
    user = product.pro.user
    transaction.on_commit(
        lambda: notify(
            user,
            "shop.product_refused",
            {"product": product.title, "reason": product.review_reason},
            link="/pro/shop/products",
        )
    )
    return product


@transaction.atomic
def unblock(product: Product, *, actor) -> Product:
    """Back to draft: the pro publishes it again (and the words are checked again)."""
    if product.status != P.BLOCKED:
        raise errors.InvalidStep()
    product.status = P.DRAFT
    product.save(update_fields=["status", "updated_at"])
    record("shop.product_unblocked", product, actor=actor)
    return product


# --- How she hands over --------------------------------------------------------------------------


@transaction.atomic
def update_shop(user, **changes) -> ShopProfile:
    shop = shop_of(pro_of(user))
    for field in ("is_open", "pickup", "seller_delivery", "partner_delivery"):
        if field in changes:
            setattr(shop, field, bool(changes[field]))
    for field, size in (("pickup_note", 300), ("partner_name", 80), ("return_policy", 1000)):
        if field in changes:
            setattr(shop, field, (changes[field] or "").strip()[:size])
    shop.save()
    return shop


def save_zone(user, *, zone_id=None, mode: str, name: str, fee_minor: int) -> DeliveryZone:
    shop = shop_of(pro_of(user))
    name = (name or "").strip()[:80]
    if mode not in ("seller", "partner") or not name or type(fee_minor) is not int or fee_minor < 0:
        raise errors.InvalidZone()
    if zone_id:
        zone = DeliveryZone.objects.filter(pk=zone_id, shop=shop).first()
        if zone is None:
            raise errors.InvalidZone()
    else:
        zone = DeliveryZone(shop=shop, position=shop.zones.count())
    zone.mode, zone.name, zone.fee_minor = mode, name, fee_minor
    zone.save()
    return zone


def delete_zone(user, zone_id) -> None:
    shop = shop_of(pro_of(user))
    deleted, _ = DeliveryZone.objects.filter(pk=zone_id, shop=shop).delete()
    if not deleted:
        raise errors.InvalidZone()
