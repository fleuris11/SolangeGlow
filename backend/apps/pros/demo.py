"""Demo showcases for local development (called by `seed_demo`).

30 pros in Cotonou, Abomey-Calavi, Porto-Novo, Paris and Brest, with services, hours,
positions, landmarks and social links. Names, places and texts are content: they are
written in French, like a real pro would. Idempotent: a showcase that already has
services is left as it is.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from decimal import Decimal

from django.contrib.gis.geos import Point
from django.utils import timezone

from .models import (
    OpeningPeriod,
    ProProfile,
    Service,
    ServiceCategory,
    ServiceOption,
    ServiceStep,
    Trade,
)
from .search import refresh_search


@dataclass
class DemoPro:
    first: str
    last: str
    phone: str
    country: str
    city: str
    district: str
    lng: float
    lat: float
    business: str
    slug: str
    trades: list[str]
    birth: str
    rating: str
    reviews: int
    verified: bool = False
    kind: str = ProProfile.Kind.INDEPENDENT
    receives: bool = True
    travels_km: int | None = None
    bio: str = ""
    landmarks: str = ""
    instagram: bool = True
    languages: list[str] = field(default_factory=list)


PROS = [
    # --- Cotonou -------------------------------------------------------------------------
    DemoPro("Aïcha", "Hounkpè", "+2290197000101", "BJ", "Cotonou", "Fidjrossè", 2.3601, 6.3552,
            "Aïcha Tresses", "aicha", ["braids"], "1994-03-12", "4.90", 128, verified=True,
            bio="Knotless, box braids et nattes collées depuis 12 ans. Mèches fournies sur demande.",
            landmarks="Après la pharmacie Fidjrossè, deuxième von à gauche, portail bleu."),
    DemoPro("Gloria", "Adjovi", "+2290196000102", "BJ", "Cotonou", "Akpakpa", 2.4468, 6.3561,
            "Gloria Make-up", "gloria", ["makeup"], "1998-07-25", "4.80", 86, verified=True,
            travels_km=12, bio="Maquillage de soirée et de mariée. Je me déplace chez toi.",
            landmarks="Face au marché Akpakpa-Dodomè, immeuble rose, 1er étage."),
    DemoPro("Nafissatou", "Bio", "+2290197000104", "BJ", "Cotonou", "Zogbo", 2.3951, 6.3872,
            "Nafi Gèle", "nafi-gele", ["headwrap"], "1987-05-18", "4.70", 54, receives=False,
            travels_km=15, bio="Attache de foulard et gèle pour mariages, baptêmes et cérémonies."),
    DemoPro("Rachida", "Soulé", "+2290161000105", "BJ", "Cotonou", "Cadjèhoun", 2.3872, 6.3603,
            "Rachida Nails", "rachida-nails", ["nails"], "2000-01-30", "4.60", 41,
            bio="Pose gel, nail art et pédicure. Hygiène stricte, matériel stérilisé.",
            landmarks="Derrière la station Cadjèhoun, salon avec l'enseigne rose."),
    DemoPro("Prisca", "Ahouansou", "+2290197000108", "BJ", "Cotonou", "Haie Vive", 2.3902, 6.3571,
            "Institut Prisca", "institut-prisca", ["skincare", "makeup"], "1985-10-04", "4.90", 173,
            verified=True, kind=ProProfile.Kind.BUSINESS,
            bio="Institut de beauté : soins du visage, gommage, épilation et maquillage.",
            landmarks="Rue des restaurants de Haie Vive, porte vitrée à côté de la boulangerie."),
    DemoPro("Bénédicta", "Gbaguidi", "+2290196000109", "BJ", "Cotonou", "Gbégamey", 2.4003, 6.3722,
            "Béné Coiffure", "bene-coiffure", ["hair"], "1992-02-14", "4.40", 37,
            bio="Défrisage, brushing, tissage et coloration. Sans rendez-vous le samedi.",
            landmarks="Carrefour Gbégamey, prendre la rue du CEG, troisième maison à droite."),
    DemoPro("Florence", "Houngbédji", "+2290166000110", "BJ", "Cotonou", "Saint-Michel", 2.4181, 6.3702,
            "Flo Couture", "flo-couture", ["sewing"], "1979-06-21", "4.80", 92, verified=True,
            bio="Robes en pagne sur mesure, tenues de cérémonie et retouches rapides.",
            landmarks="Marché Saint-Michel, allée des couturières, box 14."),
    DemoPro("Carine", "Zannou", "+2290197000111", "BJ", "Cotonou", "Agla", 2.3802, 6.3902,
            "Carine Tresses Kids", "carine-kids", ["braids"], "1996-09-30", "4.50", 29,
            bio="Tresses pour enfants, patiente et douce. Les mamans peuvent rester.",
            landmarks="Agla Hlazounto, après l'église catholique, portail vert."),
    DemoPro("Mariam", "Yessoufou", "+2290161000112", "BJ", "Cotonou", "Vèdoko", 2.4052, 6.3831,
            "Mariam Beauty", "mariam-beauty", ["makeup", "headwrap"], "1995-12-08", "4.70", 66,
            travels_km=10, bio="Maquillage et gèle assortis pour tes grands jours."),
    DemoPro("Estelle", "Akpovi", "+2290196000113", "BJ", "Cotonou", "Ganhi", 2.4251, 6.3561,
            "Salon Estelle", "salon-estelle", ["hair", "braids"], "1988-04-17", "4.30", 58,
            kind=ProProfile.Kind.BUSINESS, bio="Salon de coiffure avec 4 coiffeuses, climatisé.",
            landmarks="Ganhi, rue de la poste centrale, à côté de la banque."),
    DemoPro("Romaine", "Tchibozo", "+2290197000114", "BJ", "Cotonou", "Missèbo", 2.4302, 6.3652,
            "Romaine Ongles", "romaine-ongles", ["nails"], "2001-08-03", "4.20", 15,
            bio="Manucure et pédicure à petits prix, près du marché Missèbo.",
            landmarks="Entrée du marché Missèbo côté goudron, sous le parasol jaune."),
    DemoPro("Hortense", "Dègbo", "+2290166000115", "BJ", "Cotonou", "Dantokpa", 2.4331, 6.3721,
            "Hortense Pagne & Style", "hortense-style", ["sewing", "headwrap"], "1982-01-26", "4.60",
            47, bio="Couture wax et attache de foulard. Tissus disponibles sur place.",
            landmarks="Dantokpa, quartier des tissus, demander « Maman Hortense »."),
    # --- Abomey-Calavi -------------------------------------------------------------------
    DemoPro("Sènami", "Dossou", "+2290166000103", "BJ", "Abomey-Calavi", "Godomey", 2.3302, 6.4101,
            "Sènami Hair", "senami", ["hair", "braids"], "1990-11-02", "4.70", 64, verified=True,
            bio="Coiffure naturelle, tresses et soins des cheveux crépus.",
            landmarks="Godomey échangeur, prendre vers Togoudo, deuxième von après le kiosque."),
    DemoPro("Fifonsi", "Agbo", "+2290197000116", "BJ", "Abomey-Calavi", "Calavi centre", 2.3418, 6.4486,
            "Fifonsi Tresses", "fifonsi", ["braids"], "1997-03-19", "4.80", 102,
            bio="Spécialiste des knotless et des tresses longues. Étudiantes bienvenues.",
            landmarks="À 200 m de l'entrée de l'université, rue des photocopies, portail noir."),
    DemoPro("Yasmine", "Lawani", "+2290161000117", "BJ", "Abomey-Calavi", "Akassato", 2.3602, 6.5001,
            "Yas Nails", "yas-nails", ["nails"], "1999-05-11", "4.40", 23, receives=False,
            travels_km=8, bio="Je viens chez toi pour la manucure et la pose gel."),
    DemoPro("Odile", "Hessou", "+2290196000118", "BJ", "Abomey-Calavi", "Togba", 2.3101, 6.4602,
            "Odile Couture", "odile-couture", ["sewing"], "1975-07-07", "4.90", 81, verified=True,
            bio="Couture homme et femme, uniformes, robes de mariée sur devis.",
            landmarks="Togba, après le pont, maison avec la machine à coudre peinte sur le mur."),
    DemoPro("Linda", "Kiki", "+2290197000119", "BJ", "Abomey-Calavi", "Zogbadjè", 2.3452, 6.4202,
            "Linda Glow", "linda-glow", ["skincare"], "1993-10-22", "4.50", 33,
            bio="Soins du visage pour peaux noires et métisses, produits naturels.",
            landmarks="Zogbadjè, derrière le stade, petite cour avec des plantes."),
    # --- Porto-Novo ----------------------------------------------------------------------
    DemoPro("Mireille", "Kpadonou", "+2290197000106", "BJ", "Porto-Novo", "Ouando", 2.6201, 6.5101,
            "Mireille Couture", "mireille-couture", ["sewing"], "1983-09-09", "4.60", 49,
            bio="Couture traditionnelle et moderne, broderies faites main.",
            landmarks="Marché Ouando, sortie côté église, premier atelier à gauche.",
            languages=["fr", "yo", "guw"]),
    DemoPro("Adjoua", "Sossa", "+2290196000120", "BJ", "Porto-Novo", "Centre", 2.6051, 6.4971,
            "Adjoua Coiffure", "adjoua-coiffure", ["hair", "braids"], "1991-01-15", "4.30", 19,
            bio="Coiffure, tresses et défrisage dans une ambiance familiale.",
            landmarks="Près de la place Jean Bayol, rue de la mosquée, porte orange.",
            languages=["fr", "yo", "guw"]),
    DemoPro("Ruth", "Adékambi", "+2290161000121", "BJ", "Porto-Novo", "Tokpota", 2.6151, 6.4851,
            "Ruth Make-up", "ruth-makeup", ["makeup"], "1997-11-28", "4.70", 38, verified=True,
            travels_km=20, bio="Maquillage de mariée et de cérémonie, Porto-Novo et Cotonou.",
            languages=["fr", "yo"]),
    # --- Paris ---------------------------------------------------------------------------
    DemoPro("Clarisse", "Mensah", "+33612340107", "FR", "Paris", "Château-Rouge", 2.3491, 48.8871,
            "Clarisse Skin & Glow", "clarisse", ["skincare", "makeup"], "1991-06-14", "4.80", 112,
            verified=True, bio="Soins du visage et maquillage pour peaux mates et foncées.",
            landmarks="Sortie métro Château-Rouge, rue Poulet, code de la porte envoyé par message."),
    DemoPro("Fatou", "Diallo", "+33612340122", "FR", "Paris", "Château d'Eau", 2.3561, 48.8721,
            "Fatou Braids Paris", "fatou-braids", ["braids"], "1993-02-02", "4.90", 204,
            verified=True, kind=ProProfile.Kind.BUSINESS,
            bio="Salon de tresses afro au cœur du 10e. Knotless, fulani, nattes collées.",
            landmarks="Boulevard de Strasbourg, au fond de la galerie, salon n° 7."),
    DemoPro("Nadège", "Koffi", "+33612340123", "FR", "Paris", "Strasbourg-Saint-Denis", 2.3541,
            48.8698, "Nadège Coiffure Afro", "nadege-afro", ["hair"], "1986-08-19", "4.40", 67,
            bio="Coiffure afro et métissée : défrisage, lissage, soins profonds."),
    DemoPro("Awa", "Traoré", "+33612340124", "FR", "Paris", "Belleville", 2.3771, 48.8721,
            "Awa Nails Studio", "awa-nails", ["nails"], "1998-04-25", "4.60", 58,
            bio="Studio d'ongles : gel, capsules, nail art wax et bogolan."),
    DemoPro("Sandrine", "Kouassi", "+33612340125", "FR", "Saint-Denis", "Basilique", 2.3581,
            48.9361, "Sandrine Gèle & Make-up", "sandrine-gele", ["headwrap", "makeup"],
            "1990-12-12", "4.70", 44, travels_km=25,
            bio="Gèle et maquillage de mariage en Île-de-France, je me déplace."),
    DemoPro("Mélissa", "Bamba", "+33612340126", "FR", "Paris", "Barbès", 2.3501, 48.8838,
            "Mélissa Couture Wax", "melissa-wax", ["sewing"], "1988-03-03", "4.50", 31,
            bio="Créations en wax sur mesure, retouches et ourlets express."),
    # --- Brest ---------------------------------------------------------------------------
    DemoPro("Esther", "N'Guessan", "+33612340127", "FR", "Brest", "Siam", -4.4861, 48.3901,
            "Esther Tresses Brest", "esther-tresses", ["braids"], "1995-07-21", "4.80", 39,
            verified=True, bio="La seule spécialiste des tresses afro du centre de Brest.",
            landmarks="Rue de Siam, entrée par la cour, deuxième étage gauche."),
    DemoPro("Laure", "Ekané", "+33612340128", "FR", "Brest", "Saint-Martin", -4.4931, 48.3961,
            "Laure Beauté Noire", "laure-beaute", ["skincare", "makeup"], "1992-09-09", "4.60", 22,
            bio="Esthétique et maquillage adaptés aux peaux noires, à Brest."),
    DemoPro("Prudence", "Mbappé", "+33612340129", "FR", "Brest", "Recouvrance", -4.4991, 48.3851,
            "Prudence Coiffure", "prudence-coiffure", ["hair", "braids"], "1984-05-30", "4.30", 17,
            bio="Coiffure afro et tresses, ambiance chaleureuse de l'autre côté du pont."),
    DemoPro("Kadi", "Sylla", "+33612340130", "FR", "Brest", "Lambézellec", -4.4851, 48.4101,
            "Kadi Ongles à domicile", "kadi-ongles", ["nails"], "2000-10-10", "4.50", 12,
            receives=False, travels_km=15, bio="Manucure et pose gel chez toi, partout à Brest."),
]  # fmt: skip

# Services per trade: (name, category, price XOF, price EUR cents, kind, steps, options).
# Steps: (kind, minutes). A wait step is the time a product acts while the pro is free.
SERVICES = {
    "braids": [
        ("Knotless mi-dos", "Tresses", 15000, 12000, "fixed", [("work", 300)],
         [("Mèches fournies", 5000, 1500)]),
        ("Box braids", "Tresses", 12000, 9000, "fixed", [("work", 240)],
         [("Mèches fournies", 4000, 1200)]),
        ("Nattes collées", "Tresses", 5000, 4000, "from", [("work", 90)], []),
        ("Tresses enfant", "Enfants", 3000, 2500, "from", [("work", 60)], []),
    ],
    "hair": [
        ("Défrisage", "Coiffure", 6000, 4500, "fixed",
         [("work", 20), ("wait", 20), ("work", 40)], []),
        ("Brushing", "Coiffure", 3000, 3000, "fixed", [("work", 45)], []),
        ("Coloration", "Coiffure", 12000, 6500, "from",
         [("work", 30), ("wait", 35), ("work", 25)], []),
        ("Tissage", "Coiffure", 10000, 8000, "from", [("work", 150)],
         [("Mèches fournies", 8000, 3000)]),
    ],
    "makeup": [
        ("Maquillage de soirée", "Maquillage", 12000, 6000, "fixed", [("work", 60)], []),
        ("Maquillage mariée", "Mariage", 35000, 15000, "from", [("work", 120)],
         [("Essai la semaine avant", 10000, 5000)]),
        ("Maquillage nude", "Maquillage", 8000, 4000, "fixed", [("work", 45)], []),
    ],
    "nails": [
        ("Pose gel", "Ongles", 8000, 4500, "fixed", [("work", 75)],
         [("Nail art (2 ongles)", 1000, 500)]),
        ("Manucure simple", "Ongles", 3000, 2500, "fixed", [("work", 30)], []),
        ("Pédicure", "Pieds", 5000, 3500, "fixed", [("work", 45)], []),
    ],
    "headwrap": [
        ("Attache de foulard", "Foulard", 2500, 2000, "fixed", [("work", 20)], []),
        ("Gèle de cérémonie", "Foulard", 7500, 3000, "fixed", [("work", 30)], []),
        ("Gèle de mariage", "Mariage", 15000, 5000, "from", [("work", 45)], []),
    ],
    "sewing": [
        ("Robe en pagne sur mesure", "Sur mesure", 25000, 9000, "from", [("work", 60)],
         [("Tissu fourni", 8000, 3000)]),
        ("Tenue de cérémonie", "Sur mesure", 0, 0, "quote", [("work", 90)], []),
        ("Retouche", "Retouches", 2000, 1500, "from", [("work", 30)], []),
    ],
    "skincare": [
        ("Soin visage éclat", "Visage", 15000, 6500, "fixed", [("work", 60)], []),
        ("Gommage corps", "Corps", 10000, 4500, "fixed", [("work", 45)], []),
        ("Épilation sourcils", "Visage", 2000, 1500, "fixed", [("work", 15)], []),
    ],
}  # fmt: skip

T = datetime.time
# Opening hours: Benin, Monday to Saturday with Sunday afternoon; France, Tuesday to
# Saturday with a lunch break for the small salons.
HOURS = {
    "BJ": [(day, T(8), T(19)) for day in range(6)] + [(6, T(15), T(19))],
    "FR": [(day, T(10), T(13)) for day in range(1, 6)]
    + [(day, T(14), T(19)) for day in range(1, 6)]
    + [(5, T(9, 30), T(18))],
}


def _hours(pro: ProProfile, country: str) -> None:
    periods = HOURS[country]
    if country == "FR":
        saturday = [p for p in periods if p[0] == 5]
        periods = [p for p in periods if p[0] != 5] + saturday[-1:]
    OpeningPeriod.objects.bulk_create(
        OpeningPeriod(pro=pro, weekday=day, opens_at=opens, closes_at=closes)
        for day, opens, closes in periods
    )


def _services(pro: ProProfile, trade_keys: list[str], country: str) -> None:
    categories: dict[str, ServiceCategory] = {}
    position = 0
    for key in trade_keys:
        trade = Trade.objects.filter(key=key).first()
        for name, category, xof, eur, kind, steps, options in SERVICES[key]:
            if category not in categories:
                categories[category] = ServiceCategory.objects.create(
                    pro=pro, name=category, position=len(categories)
                )
            service = Service.objects.create(
                pro=pro,
                category=categories[category],
                trade=trade,
                name=name,
                price_kind=kind,
                price_minor=None if kind == "quote" else (xof if country == "BJ" else eur),
                currency=pro.currency,
                duration_minutes=sum(minutes for _kind, minutes in steps),
                available_at_home=pro.travels_to_clients,
                position=position,
            )
            position += 1
            ServiceStep.objects.bulk_create(
                ServiceStep(
                    service=service,
                    position=index,
                    kind=step_kind,
                    duration_minutes=minutes,
                    needs_staff=step_kind == "work",
                )
                for index, (step_kind, minutes) in enumerate(steps)
            )
            for index, (option, extra_xof, extra_eur) in enumerate(options):
                ServiceOption.objects.create(
                    service=service,
                    name=option,
                    price_minor=extra_xof if country == "BJ" else extra_eur,
                    position=index,
                )


def fill_showcase(pro: ProProfile, demo: DemoPro) -> bool:
    """Gives a demo pro her full showcase. Returns False when she already had one."""
    if pro.services.exists():
        return False
    now = timezone.now()
    pro.kind = demo.kind
    pro.business_name = demo.business
    if not ProProfile.objects.filter(slug=demo.slug).exclude(pk=pro.pk).exists():
        pro.slug = demo.slug
    pro.country = pro.user.country
    pro.currency = pro.country.default_currency.code if pro.country else "XOF"
    pro.city, pro.district = demo.city, demo.district
    pro.location = Point(demo.lng, demo.lat, srid=4326)
    pro.location_source = ProProfile.LocationSource.MAP
    pro.receives_clients = demo.receives
    pro.landmarks = demo.landmarks if demo.receives else ""
    pro.bio = demo.bio
    pro.languages = demo.languages or (["fr", "fon"] if demo.country == "BJ" else ["fr", "en"])
    links = {}
    if demo.instagram:
        links["instagram"] = "@" + demo.slug.replace("-", ".")
    if demo.country == "BJ":
        links["whatsapp"] = demo.phone
    pro.social_links = links
    if demo.travels_km:
        pro.travels_to_clients = True
        pro.service_radius_km = demo.travels_km
        pro.travel_fee_minor = 2000 if demo.country == "BJ" else 1500
    pro.rating_average = Decimal(demo.rating)
    pro.rating_count = demo.reviews
    pro.status = ProProfile.Status.PUBLISHED
    pro.published_at = now - datetime.timedelta(days=demo.reviews % 90)
    if demo.verified:
        pro.verification_status = ProProfile.Verification.VERIFIED
        pro.verified_at = now
    pro.save()
    pro.trades.set(Trade.objects.filter(key__in=demo.trades))
    _services(pro, demo.trades, demo.country)
    _hours(pro, demo.country)
    refresh_search(pro)
    return True
