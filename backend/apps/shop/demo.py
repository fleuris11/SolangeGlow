"""Demo shops (called by `seed_demo`): products with shades and sizes, delivery zones, a
promo code, a flash sale, a bundle, and handed-over orders with verified reviews.

Pictures are flat drawings of the products in the brand palette (no real photo yet).
Idempotent: a shop gets its products once; the flash sale is renewed when none runs.
"""

from __future__ import annotations

import datetime
import io
import random
import uuid
from dataclasses import dataclass, field

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFilter

from apps.accounts.models import User
from apps.core.errors import DomainError
from apps.core.media.models import MediaAsset
from apps.core.media.processing import process
from apps.payments import services as payment_services
from apps.payments.services import groups as group_services
from apps.pros.models import ProProfile
from apps.social.models import Review
from apps.social.services import recompute_rating

from .models import Bundle, BundleItem, DeliveryZone, FlashSale, Order, Product, PromoCode
from .selectors import shop_of
from .services import cart, checkout, orders

W = H = 1080
BACKGROUNDS = [(249, 225, 231), (255, 247, 245), (246, 230, 200), (226, 240, 232), (238, 228, 245)]
ACCENTS = [(200, 16, 46), (232, 176, 75), (31, 122, 90), (59, 18, 51), (122, 78, 110)]


@dataclass
class DemoProduct:
    title: str
    category: str
    price: int
    drawing: str  # bottle, lipstick, jar, palette, wig, fabric, polish, perfume, bag, dress
    description: str
    stock: int = 40
    prep_days: int = 1
    variants: list[dict] = field(default_factory=list)


SHADES = [
    {"shade": "Porcelaine dorée", "swatch": "#E6B98F", "stock": 12},
    {"shade": "Caramel", "swatch": "#B07A4F", "stock": 30},
    {"shade": "Cannelle", "swatch": "#8A5533", "stock": 25},
    {"shade": "Ébène", "swatch": "#4A2B1A", "stock": 0},
]
LIPS = [
    {"shade": "Hibiscus", "swatch": "#C8102E", "stock": 20},
    {"shade": "Prune", "swatch": "#5B1F45", "stock": 15},
    {"shade": "Nude cacao", "swatch": "#8C5A4A", "stock": 18},
]
WIG_SIZES = [
    {"size": "12 pouces", "stock": 4},
    {"size": "18 pouces", "stock": 6, "price_minor": 65_000},
    {"size": "24 pouces", "stock": 2, "price_minor": 85_000},
]
DRESS_SIZES = [{"size": s, "stock": 3} for s in ("S", "M", "L", "XL")]

SHOPS: dict[str, dict] = {
    "gloria": {
        "zones": [("seller", "Cotonou centre", 1_000), ("seller", "Abomey-Calavi", 2_000)],
        "partner": ("Gozem", [("partner", "Tout Cotonou", 1_500)]),
        "pickup_note": "Du lundi au samedi, 10 h - 19 h.",
        "promo": ("BIENVENUE", 10),
        "products": [
            DemoProduct(
                "Fond de teint Velours",
                "makeup",
                8_000,
                "bottle",
                "Fond de teint fluide pour peaux foncées et métissées, fini mat, tenue 12 heures. "
                "Ne file pas avec la chaleur.",
                variants=SHADES,
            ),
            DemoProduct(
                "Rouge à lèvres Wax",
                "makeup",
                3_500,
                "lipstick",
                "Couleurs intenses, texture crème, ne dessèche pas les lèvres.",
                variants=LIPS,
            ),
            DemoProduct(
                "Palette Soleil d'Afrique",
                "makeup",
                12_000,
                "palette",
                "12 fards à paupières mats et irisés, pigments riches pour peaux foncées.",
                stock=10,
            ),
            DemoProduct(
                "Kit pinceaux voyage",
                "accessories",
                6_500,
                "bag",
                "8 pinceaux doux et leur trousse en pagne.",
                stock=8,
            ),
            DemoProduct(
                "Fixateur de maquillage",
                "makeup",
                5_000,
                "perfume",
                "Brume fixante : le maquillage tient même par 35 °C.",
            ),
        ],
    },
    "institut-prisca": {
        "zones": [("seller", "Haie Vive et Cadjèhoun", 500), ("seller", "Tout Cotonou", 1_000)],
        "pickup_note": "À l'accueil de l'institut, 9 h - 20 h.",
        "bundle": ("Routine éclat", 17_000),
        "products": [
            DemoProduct(
                "Beurre de karité pur",
                "skincare",
                2_500,
                "jar",
                "Karité non raffiné du nord Bénin, pour le corps, le visage et les cheveux.",
                variants=[
                    {"size": "100 g", "stock": 40},
                    {"size": "250 g", "stock": 25, "price_minor": 5_000},
                ],
            ),
            DemoProduct(
                "Savon noir au moringa",
                "skincare",
                1_500,
                "jar",
                "Savon artisanal, nettoie en douceur les peaux mixtes.",
            ),
            DemoProduct(
                "Sérum visage baobab",
                "skincare",
                9_500,
                "bottle",
                "Huile de baobab et vitamine E : hydrate sans briller.",
                stock=12,
            ),
            DemoProduct(
                "Gommage au café",
                "skincare",
                4_000,
                "jar",
                "Grains de café du Bénin et huile de coco : peau douce dès la première fois.",
            ),
            DemoProduct(
                "Crème mains au cacao",
                "skincare",
                3_000,
                "jar",
                "Nourrit les mains sèches, parfum gourmand.",
                stock=2,
            ),
        ],
    },
    "aicha": {
        "zones": [("seller", "Fidjrossè et environs", 1_000)],
        "pickup_note": "Au salon, sur rendez-vous ou sans.",
        "products": [
            DemoProduct(
                "Mèches X-pression",
                "hair",
                1_500,
                "wig",
                "Mèches pour box braids et knotless, ne grattent pas.",
                variants=[
                    {"color": "Noir 1B", "stock": 60},
                    {"color": "Châtain 30", "stock": 30},
                    {"color": "Bordeaux", "stock": 20},
                ],
            ),
            DemoProduct(
                "Perruque lace frontale",
                "hair",
                45_000,
                "wig",
                "Cheveux naturels brésiliens, lace transparente, se coiffe comme tu veux. "
                "Préparée et ajustée à ta tête.",
                prep_days=5,
                variants=WIG_SIZES,
            ),
            DemoProduct(
                "Huile pousse ricin",
                "hair",
                3_500,
                "bottle",
                "Huile de ricin noire pour les pointes et les tempes.",
            ),
            DemoProduct(
                "Bonnet en satin",
                "accessories",
                2_000,
                "bag",
                "Protège tes tresses la nuit.",
                variants=[{"color": "Rose", "stock": 15}, {"color": "Noir", "stock": 20}],
            ),
        ],
    },
    "flo-couture": {
        "zones": [("seller", "Cotonou", 1_500)],
        "partner": ("Zem du marché", [("partner", "Porto-Novo", 3_000)]),
        "pickup_note": "Marché Saint-Michel, box 14.",
        "products": [
            DemoProduct(
                "Pagne wax hollandais 6 yards",
                "fabrics",
                18_000,
                "fabric",
                "Wax 100 % coton, couleurs qui ne déteignent pas.",
                variants=[
                    {"color": "Fleurs de mariage", "stock": 8},
                    {"color": "Œil de Dieu", "stock": 5},
                ],
            ),
            DemoProduct(
                "Robe sirène en pagne",
                "clothing",
                35_000,
                "dress",
                "Cousue à tes mesures après la commande : envoie-moi tes mesures par message.",
                prep_days=7,
                variants=DRESS_SIZES,
            ),
            DemoProduct(
                "Foulard aso-oke",
                "accessories",
                12_000,
                "fabric",
                "Pour les gèle de cérémonie, tissé à la main.",
                stock=6,
            ),
            DemoProduct(
                "Sac en wax",
                "accessories",
                9_000,
                "bag",
                "Sac à main doublé, assorti à tes tenues.",
                stock=4,
            ),
        ],
    },
    "senami": {
        "zones": [("seller", "Godomey et Calavi", 1_000)],
        "pickup_note": "Au salon de Godomey.",
        "products": [
            DemoProduct(
                "Masque hydratant à l'avocat",
                "hair",
                4_500,
                "jar",
                "Pour cheveux crépus secs : 20 minutes de pose, cheveux souples.",
            ),
            DemoProduct(
                "Spray démêlant",
                "hair",
                3_000,
                "perfume",
                "Démêle sans casser, idéal pour les enfants.",
            ),
            DemoProduct(
                "Peigne démêloir en bois",
                "accessories",
                1_500,
                "bag",
                "Dents larges, ne casse pas les cheveux.",
            ),
        ],
    },
    "ruth-makeup": {
        "zones": [("seller", "Porto-Novo", 1_000)],
        "pickup_note": "Tokpota, maison à côté de la boutique de pagnes.",
        "products": [
            DemoProduct(
                "Vernis Or de Ouidah",
                "nails",
                2_000,
                "polish",
                "Vernis pailleté, séchage rapide.",
                variants=[
                    {"shade": "Or", "swatch": "#E8B04B", "stock": 20},
                    {"shade": "Rouge", "swatch": "#C8102E", "stock": 20},
                ],
            ),
            DemoProduct(
                "Faux cils naturels",
                "makeup",
                2_500,
                "palette",
                "Cils légers, réutilisables 10 fois.",
            ),
            DemoProduct(
                "Parfum Jasmin de nuit",
                "fragrance",
                15_000,
                "perfume",
                "Eau de parfum 50 ml, notes de jasmin et de vanille.",
                stock=7,
            ),
        ],
    },
    "clarisse": {
        "zones": [("partner", "Île-de-France", 590)],
        "partner_only": ("Colissimo", None),
        "pickup_note": "Château-Rouge, sur rendez-vous.",
        "products": [
            DemoProduct(
                "Huile de karité fouettée",
                "skincare",
                1_490,
                "jar",
                "Karité fouetté à la vanille, fabriqué à Paris.",
            ),
            DemoProduct(
                "Gloss Miel",
                "makeup",
                1_200,
                "lipstick",
                "Gloss non collant, reflets dorés.",
                variants=[{"shade": "Miel", "swatch": "#C98B3C", "stock": 25}],
            ),
            DemoProduct(
                "Bandeau en wax",
                "accessories",
                990,
                "fabric",
                "Bandeau élastique, taille unique.",
            ),
        ],
    },
    "fatou-braids": {
        "zones": [("partner", "Paris intra-muros", 490)],
        "partner_only": ("Coursier Stuart", None),
        "products": [
            DemoProduct(
                "Perruque afro kinky",
                "hair",
                8_900,
                "wig",
                "Effet naturel, bonnet confortable.",
                prep_days=3,
                variants=[
                    {"size": "14 pouces", "stock": 3},
                    {"size": "18 pouces", "stock": 2, "price_minor": 10_900},
                ],
            ),
            DemoProduct(
                "Gel bords Edge control",
                "hair",
                990,
                "jar",
                "Tenue forte, sans résidu blanc.",
            ),
        ],
    },
}

REVIEWS = [
    (5, "Produit conforme, bien emballé, et la vendeuse est adorable."),
    (5, "Je recommande, la teinte est parfaite pour ma peau."),
    (4, "Très bon produit, livraison un peu longue mais ça vaut le coup."),
]


# --- Pictures ------------------------------------------------------------------------------------


def _draw(seed: str, drawing: str) -> bytes:
    rng = random.Random(seed)  # noqa: S311  (pictures, not security)
    image = Image.new("RGB", (W, H), rng.choice(BACKGROUNDS))
    draw = ImageDraw.Draw(image)
    accent, second = rng.sample(ACCENTS, 2)
    gold = (232, 176, 75)
    if drawing == "bottle":
        draw.rounded_rectangle([390, 330, 690, 900], 60, fill=accent)
        draw.rounded_rectangle([470, 190, 610, 340], 20, fill=(40, 22, 26))
        draw.rounded_rectangle([430, 520, 650, 700], 16, fill=(255, 255, 255))
    elif drawing == "lipstick":
        draw.rounded_rectangle([420, 560, 660, 940], 30, fill=gold)
        draw.rectangle([450, 360, 630, 580], fill=(40, 22, 26))
        draw.polygon([(470, 360), (610, 360), (610, 250), (470, 320)], fill=accent)
    elif drawing == "jar":
        draw.rounded_rectangle([300, 520, 780, 900], 80, fill=(255, 255, 255))
        draw.rounded_rectangle([280, 420, 800, 540], 40, fill=accent)
        draw.ellipse([440, 640, 640, 780], fill=second)
    elif drawing == "palette":
        draw.rounded_rectangle([200, 320, 880, 780], 50, fill=(40, 22, 26))
        for row in range(3):
            for col in range(4):
                color = rng.choice([*ACCENTS, gold, (200, 120, 60), (150, 60, 120)])
                x, y = 260 + col * 150, 380 + row * 130
                draw.ellipse([x, y, x + 110, y + 110], fill=color)
    elif drawing == "wig":
        draw.ellipse([320, 240, 760, 700], fill=(36, 16, 24))
        draw.rectangle([320, 470, 760, 920], fill=(36, 16, 24))
        draw.ellipse([420, 330, 660, 640], fill=(198, 138, 94))
        draw.rectangle([470, 640, 610, 920], fill=(198, 138, 94))
    elif drawing in ("fabric", "dress"):
        if drawing == "dress":
            draw.polygon(
                [(430, 220), (650, 220), (720, 600), (820, 980), (260, 980), (360, 600)],
                fill=accent,
            )
        else:
            draw.rounded_rectangle([180, 260, 900, 860], 30, fill=accent)
        for _ in range(70):
            x, y = rng.randint(240, 840), rng.randint(280, 940)
            size = rng.randint(14, 34)
            draw.ellipse([x - size, y - size, x + size, y + size], fill=second)
    elif drawing == "polish":
        draw.rounded_rectangle([400, 480, 680, 900], 70, fill=accent)
        draw.rectangle([480, 260, 600, 490], fill=(40, 22, 26))
    elif drawing == "perfume":
        draw.rounded_rectangle([350, 420, 730, 900], 120, fill=accent)
        draw.rectangle([490, 300, 590, 430], fill=gold)
        draw.ellipse([470, 230, 610, 330], fill=gold)
    else:  # bag
        draw.rounded_rectangle([260, 420, 820, 900], 60, fill=accent)
        draw.arc([380, 240, 700, 560], 180, 360, fill=(40, 22, 26), width=30)
    for _ in range(10):
        x, y = rng.randint(120, 960), rng.randint(80, 220)
        draw.regular_polygon((x, y, rng.randint(10, 20)), 4, rotation=45, fill=gold)
    image = image.filter(ImageFilter.SMOOTH)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=86)
    return buffer.getvalue()


def _picture(owner, seed: str, drawing: str) -> MediaAsset:
    asset = MediaAsset(
        id=uuid.uuid4(),
        owner=owner,
        kind=MediaAsset.Kind.IMAGE,
        purpose="product_photo",
        visibility=MediaAsset.Visibility.PUBLIC,
        original_name=f"{seed}.jpg",
        content_type="image/jpeg",
    )
    data = _draw(seed, drawing)
    asset.size_bytes = len(data)
    asset.original.save(f"{seed}.jpg", ContentFile(data), save=False)
    asset.save()
    process(asset)
    return asset


# --- Shops ---------------------------------------------------------------------------------------


def _fill(pro: ProProfile, data: dict) -> int:
    from .services import catalog

    owner = pro.user
    shop = shop_of(pro)
    shop.pickup = True
    shop.pickup_note = data.get("pickup_note", "")
    shop.seller_delivery = any(mode == "seller" for mode, _, _ in data["zones"])
    partner = data.get("partner") or data.get("partner_only")
    shop.partner_delivery = bool(partner) or any(m == "partner" for m, _, _ in data["zones"])
    shop.partner_name = partner[0] if partner else ""
    shop.return_policy = "Échange possible sous 3 jours si le produit n'a pas été ouvert."
    shop.save()
    zones = list(data["zones"]) + (list(data["partner"][1]) if data.get("partner") else [])
    for position, (mode, name, fee) in enumerate(zones):
        DeliveryZone.objects.get_or_create(
            shop=shop, name=name, defaults={"mode": mode, "fee_minor": fee, "position": position}
        )
    created = 0
    for index, item in enumerate(data["products"]):
        if Product.objects.filter(pro=pro, title=item.title).exists():
            continue
        seed = f"{pro.slug}-{index}"
        photos = [_picture(owner, seed, item.drawing)]
        if index % 2 == 0:
            photos.append(_picture(owner, seed + "-b", item.drawing))
        product = catalog.save_product(
            owner,
            title=item.title,
            price_minor=item.price,
            category_key=item.category,
            description=item.description,
            prep_days=item.prep_days,
            photo_ids=[p.pk for p in photos],
            variants=item.variants or [{"stock": item.stock}],
        )
        catalog.publish(owner, product)
        created += 1
    if data.get("promo"):
        code, percent = data["promo"]
        PromoCode.objects.get_or_create(
            pro=pro, code=code, defaults={"percent_off": percent, "currency": pro.currency}
        )
    if data.get("bundle") and not Bundle.objects.filter(pro=pro).exists():
        title, price = data["bundle"]
        bundle = Bundle.objects.create(
            pro=pro,
            title=title,
            price_minor=price,
            currency=pro.currency,
            description="Karité, gommage et sérum : la routine complète à prix doux.",
        )
        for product in Product.objects.filter(
            pro=pro, title__in=["Beurre de karité pur", "Gommage au café", "Sérum visage baobab"]
        ):
            BundleItem.objects.create(bundle=bundle, variant=product.variants.first())
    return created


def _flash_sale(pro: ProProfile) -> None:
    now = timezone.now()
    product = Product.objects.filter(pro=pro, title="Palette Soleil d'Afrique").first()
    if product and not FlashSale.objects.filter(product=product, ends_at__gt=now).exists():
        FlashSale.objects.create(
            product=product,
            percent_off=25,
            starts_at=now - datetime.timedelta(hours=1),
            ends_at=now + datetime.timedelta(days=2),
            quantity_limit=20,
            announced_at=now,
        )


def _past_orders(pros: dict, rng: random.Random) -> int:
    """A few handed-over orders with their verified review (only once)."""
    clients = list(User.objects.filter(phone__in=["+2290197000201", "+2290196000202"]))
    if not clients or Order.objects.filter(buyer__in=clients).exists():
        return 0
    count = 0
    for slug in ("gloria", "institut-prisca", "aicha"):
        pro = pros.get(slug)
        if pro is None:
            continue
        product = Product.objects.filter(pro=pro, status="published").order_by("created_at").first()
        variant = product.variants.filter(stock__gt=0).first() if product else None
        if variant is None:
            continue
        client = clients[count % len(clients)]
        try:
            cart.add(client, variant_id=variant.pk)
            group, [order] = checkout.place_orders(
                client, [checkout.ShopChoice(pro_id=pro.pk, delivery_mode="pickup")]
            )
        except DomainError:  # demo data: payments may be off here
            continue
        group_services.mark_group_paid(
            group, amount_minor=group.total_minor, currency=group.currency, key=f"demo:{group.pk}"
        )
        order.refresh_from_db()
        orders.ready_for_pickup(pro.user, order)
        code = payment_services.receipt_code_for(order.payment, client)
        payment_services.confirm_receipt(order.payment, code, actor=pro.user)
        rating, text = rng.choice(REVIEWS)
        Review.objects.get_or_create(
            source_type="order",
            source_id=order.pk,
            defaults={"author": client, "pro": pro, "rating": rating, "text": text},
        )
        recompute_rating(pro.pk)
        count += 1
    return count


def seed_shop(rng: random.Random | None = None) -> dict:
    rng = rng or random.Random(9)  # noqa: S311  (demo data)
    pros = {
        p.slug: p
        for p in ProProfile.objects.filter(
            slug__in=SHOPS, status=ProProfile.Status.PUBLISHED
        ).select_related("user", "country")
    }
    counts = {"shops": 0, "products": 0, "orders": 0}
    for slug, data in SHOPS.items():
        pro = pros.get(slug)
        if pro is None or not pro.is_verified:
            continue
        with transaction.atomic():
            counts["products"] += _fill(pro, data)
        counts["shops"] += 1
    if "gloria" in pros:
        _flash_sale(pros["gloria"])
    counts["orders"] = _past_orders(pros, rng)
    return counts
