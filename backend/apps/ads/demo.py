"""Demo of the ads (seed_demo): a brand campaign in Cotonou (banner, feed; a launch screen
kept as a draft), a sponsored France Selection product, three house promotions as
fillers, and a boost of Aïcha already running."""

from __future__ import annotations

import datetime

from django.utils import timezone

from apps.accounts.models import User
from apps.payments import services as payment_services
from apps.payments.models import Payment
from apps.pros.models import ProProfile
from apps.selection_france.models import SelectionProduct
from apps.social.demo import _picture

from .models import Advertiser, Boost, Campaign, Creative, CreativeMedia
from .services import boosts, common

AICHA = "+2290197000101"

HOUSE = [
    (
        "Offrir au pays",
        "Offre une coiffure à ta mère, payée en euros.",
        "Offrir",
        "/offrir",
        "hair",
    ),
    (
        "Sélection France",
        "Les produits tendance de France, livrés au Bénin.",
        "Voir",
        "/selection",
        "makeup",
    ),
    (
        "Académie",
        "Apprends un métier de la beauté à ton rythme.",
        "Apprendre",
        "/academie",
        "braids",
    ),
]


def _owner():
    return User.objects.filter(is_staff=True).first() or User.objects.filter(phone=AICHA).first()


def _campaign(advertiser, name, kind, days=30, **values) -> Campaign:
    now = timezone.now()
    return Campaign.objects.create(
        advertiser=advertiser,
        name=name,
        kind=kind,
        status=Campaign.Status.ACTIVE,
        starts_at=now - datetime.timedelta(days=1),
        ends_at=now + datetime.timedelta(days=days),
        **values,
    )


def _creative(campaign, owner, *, seed, trade, placements, **values) -> Creative:
    creative = Creative.objects.create(
        campaign=campaign,
        name=values.get("title") or campaign.name,
        placements=placements,
        **values,
    )
    if owner is not None and values.get("format") != Creative.Format.NATIVE:
        CreativeMedia.objects.create(
            creative=creative, media=_picture(owner, seed, trade, purpose="ad_media")
        )
    return creative


def seed_ads() -> dict:
    if Campaign.objects.filter(kind=Campaign.Kind.SOLD).exists():
        return {"campaigns": 0}
    owner = _owner()
    karite = Advertiser.objects.create(
        name="Karité Doux Cotonou", kind=Advertiser.Kind.BUSINESS, contact_name="Mme Houngbo"
    )
    sold = _campaign(
        karite,
        "Karité Doux — rentrée",
        Campaign.Kind.SOLD,
        priority=7,
        pricing=Campaign.Pricing.FLAT,
        price_minor=150_000,
        currency="XOF",
        countries=["BJ"],
        max_per_day=3,
    )
    _creative(
        sold,
        owner,
        seed="ad-karite",
        trade="skincare",
        placements=["home_banner", "feed"],
        format=Creative.Format.IMAGE,
        title="Le karité qui nourrit tes cheveux",
        text="Beurre de karité pur du nord du Bénin. -10 % ce mois-ci.",
        cta="Voir la boutique",
        link="/explore?trade=skincare",
    )
    # The launch screen covers the app once a day: an example kept as a draft, started
    # from the admin (« Start ») to see it.
    splash = Campaign.objects.create(
        advertiser=karite,
        name="Karité Doux — écran de lancement (exemple)",
        kind=Campaign.Kind.SOLD,
        status=Campaign.Status.DRAFT,
        starts_at=sold.starts_at,
        ends_at=sold.ends_at,
        countries=["BJ"],
        max_per_day=1,
    )
    _creative(
        splash,
        owner,
        seed="ad-karite-splash",
        trade="skincare",
        placements=["splash"],
        format=Creative.Format.IMAGE,
        title="Karité Doux",
        text="Le soin du Bénin pour tes cheveux et ta peau.",
        cta="Découvrir",
        link="/explore?trade=skincare",
    )
    product = SelectionProduct.objects.filter(availability="available").first()
    if product is not None:
        _creative(
            sold,
            owner,
            seed="ad-product",
            trade="makeup",
            placements=["product"],
            format=Creative.Format.NATIVE,
            selection_product=product,
        )
    house = Advertiser.objects.filter(
        kind=Advertiser.Kind.HOUSE
    ).first() or Advertiser.objects.create(name="Solange Glow", kind=Advertiser.Kind.HOUSE)
    for title, text, cta, link, trade in HOUSE:
        promo = _campaign(house, title, Campaign.Kind.HOUSE, days=365, priority=3, max_per_day=5)
        _creative(
            promo,
            owner,
            seed=f"ad-house-{trade}",
            trade=trade,
            placements=["home_banner", "feed", "product"],
            format=Creative.Format.IMAGE,
            title=title,
            text=text,
            cta=cta,
            link=link,
        )
    aicha = ProProfile.objects.filter(user__phone=AICHA).first()
    if aicha is not None and not Boost.objects.filter(pro=aicha).exists():
        boost = boosts.buy(aicha, "week", actor=aicha.user)
        payment = Payment.objects.get(pk=boost.payment_id)
        payment_services.mark_paid(
            payment,
            amount_minor=payment.total_minor,
            currency=payment.currency,
            key=f"demo:{payment.pk}",
        )
    common.changed()
    return {"campaigns": Campaign.objects.count()}
