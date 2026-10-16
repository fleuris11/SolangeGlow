"""Demo France Selection (called by `seed_demo`): products of the three aisles, pick-up
points, a group pre-order and a quoted special request. Idempotent."""

from __future__ import annotations

import datetime
import uuid

from django.core.files.base import ContentFile
from django.utils import timezone

from apps.accounts.models import User
from apps.core.media.models import MediaAsset
from apps.core.media.processing import process
from apps.shop.demo import _draw

from . import services
from .models import (
    GroupBuy,
    PickupPoint,
    SelectionCategory,
    SelectionPhoto,
    SelectionProduct,
    SpecialRequest,
)

POINTS = [
    (
        "Solange Glow Haie Vive",
        "Cotonou",
        "Haie Vive, rue des restaurants",
        "À côté de la boulangerie",
        "Lundi au samedi, 10 h - 19 h",
    ),
    (
        "Sènami Hair (Godomey)",
        "Abomey-Calavi",
        "Godomey, vers Togoudo",
        "Deuxième von après le kiosque",
        "Mardi au samedi, 9 h - 18 h",
    ),
]

# title, slug, merchant, url, euro cents, grams, aisle, category, drawing, options, description
PRODUCTS = [
    (
        "Mini mascara volume",
        "mini-mascara-volume",
        "Sephora",
        "https://www.sephora.fr/",
        690,
        40,
        "small_prices",
        "makeup",
        "lipstick",
        [],
        "Format voyage, noir intense.",
    ),
    (
        "Baume à lèvres teinté",
        "baume-levres-teinte",
        "Nocibé",
        "https://www.nocibe.fr/",
        590,
        30,
        "small_prices",
        "makeup",
        "lipstick",
        ["Rose", "Cerise"],
        "Hydrate et colore légèrement.",
    ),
    (
        "Pinces à cheveux dorées (lot de 6)",
        "pinces-cheveux-dorees",
        "Zara",
        "https://www.zara.com/fr/",
        799,
        80,
        "small_prices",
        "accessories",
        "bag",
        [],
        "Pour tresses et chignons.",
    ),
    (
        "Crème mains karité mini",
        "creme-mains-karite-mini",
        "L'Occitane",
        "https://fr.loccitane.com/",
        600,
        40,
        "small_prices",
        "skincare",
        "jar",
        [],
        "Le classique en petit format.",
    ),
    (
        "Éponge à maquillage",
        "eponge-maquillage",
        "Sephora",
        "https://www.sephora.fr/",
        690,
        30,
        "small_prices",
        "makeup",
        "palette",
        [],
        "Pour un teint sans traces.",
    ),
    (
        "Fond de teint Fenty Pro Filt'r",
        "fond-de-teint-fenty",
        "Sephora",
        "https://www.sephora.fr/",
        3900,
        150,
        "trending",
        "makeup",
        "bottle",
        ["330", "385", "430", "470", "498"],
        "50 teintes, tenue longue durée. Le fond de teint qui buzze.",
    ),
    (
        "Gloss Fenty Gloss Bomb",
        "gloss-fenty-gloss-bomb",
        "Sephora",
        "https://www.sephora.fr/",
        2300,
        60,
        "trending",
        "makeup",
        "lipstick",
        ["Fenty Glow", "Hot Chocolit"],
        "Brillance qui va à toutes les carnations.",
    ),
    (
        "Huile Mielle romarin et menthe",
        "huile-mielle-romarin",
        "Amazon",
        "https://www.amazon.fr/",
        1199,
        150,
        "trending",
        "hair",
        "bottle",
        [],
        "L'huile de pousse vue partout sur TikTok.",
    ),
    (
        "Sérum The Ordinary niacinamide",
        "serum-the-ordinary-niacinamide",
        "Sephora",
        "https://www.sephora.fr/",
        790,
        60,
        "trending",
        "skincare",
        "bottle",
        [],
        "Resserre les pores, unifie le teint.",
    ),
    (
        "Bonnet en satin réversible",
        "bonnet-satin-reversible",
        "Amazon",
        "https://www.amazon.fr/",
        1299,
        80,
        "trending",
        "accessories",
        "bag",
        ["Noir", "Rose poudré"],
        "Protège les cheveux la nuit.",
    ),
    (
        "Sèche-cheveux Dyson Supersonic",
        "seche-cheveux-dyson",
        "Dyson",
        "https://www.dyson.fr/",
        39900,
        1800,
        "luxury",
        "hair",
        "bag",
        [],
        "Le sèche-cheveux des pros, avec ses embouts pour cheveux crépus.",
    ),
    (
        "Sac Polène Numéro Un",
        "sac-polene-numero-un",
        "Polène",
        "https://www.polene-paris.com/",
        39000,
        900,
        "luxury",
        "fashion",
        "bag",
        ["Noir", "Camel"],
        "Cuir de vachette, fabriqué en Espagne.",
    ),
    (
        "Palette Pat McGrath",
        "palette-pat-mcgrath",
        "Sephora",
        "https://www.sephora.fr/",
        6500,
        250,
        "luxury",
        "makeup",
        "palette",
        [],
        "Pigments intenses, emballage soigné.",
    ),
    (
        "Crème La Mer",
        "creme-la-mer",
        "Sephora",
        "https://www.sephora.fr/",
        19000,
        300,
        "luxury",
        "skincare",
        "jar",
        [],
        "La crème légendaire, 30 ml.",
    ),
    (
        "Eau de parfum Baccarat Rouge",
        "parfum-baccarat-rouge",
        "Sephora",
        "https://www.sephora.fr/",
        21500,
        400,
        "luxury",
        "fragrance",
        "perfume",
        [],
        "Bloqué tant que les parfums ne voyagent pas en avion.",
    ),
]


def _photo(owner, seed: str, drawing: str) -> MediaAsset:
    asset = MediaAsset(
        id=uuid.uuid4(),
        owner=owner,
        kind=MediaAsset.Kind.IMAGE,
        purpose="selection_photo",
        visibility=MediaAsset.Visibility.PUBLIC,
        original_name=f"{seed}.jpg",
        content_type="image/jpeg",
    )
    data = _draw(f"selection-{seed}", drawing)
    asset.size_bytes = len(data)
    asset.original.save(f"{seed}.jpg", ContentFile(data), save=False)
    asset.save()
    process(asset)
    return asset


def seed_selection() -> dict:
    counts = {"products": 0, "points": 0}
    for position, (name, city, address, landmarks, hours) in enumerate(POINTS):
        _, created = PickupPoint.objects.get_or_create(
            name=name,
            defaults={
                "city": city,
                "address": address,
                "landmarks": landmarks,
                "hours": hours,
                "position": position,
            },
        )
        counts["points"] += created
    house = services.selectors.house_account()
    categories = {c.key: c for c in SelectionCategory.objects.all()}
    for title, slug, merchant, url, cents, grams, aisle, key, drawing, options, text in PRODUCTS:
        if SelectionProduct.objects.filter(slug=slug).exists():
            continue
        product = SelectionProduct.objects.create(
            title=title,
            slug=slug,
            merchant_name=merchant,
            merchant_url=url,
            purchase_price_cents=cents,
            weight_grams=grams,
            aisle=aisle,
            category=categories[key],
            options=options,
            description=text,
        )
        SelectionPhoto.objects.create(product=product, media=_photo(house, slug, drawing))
        services.reprice(product)
        counts["products"] += 1

    trending = SelectionProduct.objects.filter(slug="huile-mielle-romarin").first()
    now = timezone.now()
    if trending and not GroupBuy.objects.filter(product=trending, ends_at__gt=now).exists():
        GroupBuy.objects.create(
            product=trending,
            target_quantity=20,
            price_xof=max(trending.price_xof - 2_000, 1_000),
            ends_at=now + datetime.timedelta(days=6),
        )
    awa = User.objects.filter(phone="+2290197000201").first()
    if awa and not SpecialRequest.objects.filter(client=awa).exists():
        request = SpecialRequest.objects.create(
            client=awa,
            link="https://www.zara.com/fr/",
            note="Cette robe en taille M, couleur verte.",
            title="Robe longue satinée",
            merchant_name="Zara",
            merchant_url="https://www.zara.com/fr/",
            purchase_price_cents=4_595,
            weight_grams=400,
            category=categories["fashion"],
        )
        services.send_quote(request, actor=None)
    return counts
