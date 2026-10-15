"""Products: variants and stock, the forbidden words, publication, the team's review."""

import pytest

from apps.core.tests.factories import PlatformSettingFactory
from apps.moderation.models import ModerationCase
from apps.notifications.models import Notification
from apps.pros.models import ProProfile
from apps.shop import errors, forbidden
from apps.shop.models import CartItem, ForbiddenTerm, Product, ShopProfile, Variant
from apps.shop.services import cart, catalog

from .factories import buyer, delivers, photo, product, shop_owner

pytestmark = pytest.mark.django_db
P = Product.Status


def test_a_product_with_shades_and_stock():
    owner = shop_owner()
    item = product(
        owner,
        variants=[
            {"shade": "Caramel", "swatch": "#A0522D", "stock": 4},
            {"shade": "Ébène", "swatch": "#3B2417", "stock": 0, "price_minor": 9_000},
        ],
    )
    assert item.status == P.PUBLISHED and item.published_at and item.slug == "fond-de-teint-velours"
    caramel, ebene = item.variants.order_by("position")
    assert caramel.label == "Caramel" and caramel.base_price_minor == 8_000
    assert ebene.base_price_minor == 9_000 and str(ebene) == "Fond de teint Velours Ébène"
    assert item.author == owner and "Tenue" in item.text and str(item) == item.title


def test_same_title_gets_another_link():
    owner = shop_owner()
    first = product(owner, publish=False)
    second = product(owner, publish=False)
    assert (first.slug, second.slug) == ("fond-de-teint-velours", "fond-de-teint-velours-2")
    renamed = catalog.save_product(
        owner, product=second, title="Gloss Miel", price_minor=3_000, variants=[{"stock": 1}]
    )
    assert renamed.slug == "gloss-miel"


@pytest.mark.parametrize(
    "variants",
    [
        [{"shade": "A", "stock": 1}, {"shade": "a", "stock": 2}],  # the same twice
        [{"shade": "A", "stock": 1}, {"stock": 2}],  # a choice without a name
        [{"stock": -1}],
        [{"stock": 1, "swatch": "red"}],
        [{"stock": 1, "price_minor": 0}],
    ],
)
def test_wrong_variants_are_refused(variants):
    with pytest.raises(errors.InvalidVariants):
        product(variants=variants, publish=False)


def test_product_rules():
    owner = shop_owner()
    with pytest.raises(errors.IncompleteProduct):
        catalog.save_product(owner, title=" ", price_minor=100)
    with pytest.raises(errors.IncompleteProduct):
        catalog.save_product(owner, title="Gloss", price_minor=0)
    with pytest.raises(errors.IncompleteProduct):
        catalog.save_product(owner, title="Gloss", price_minor=100, prep_days=61)
    with pytest.raises(errors.IncompleteProduct):
        catalog.save_product(owner, title="Gloss", price_minor=100, category_key="unknown")
    PlatformSettingFactory(key="shop.max_photos", value="1")
    with pytest.raises(errors.TooManyPhotos):
        catalog.save_product(
            owner, title="Gloss", price_minor=100, photo_ids=[photo(owner).pk, photo(owner).pk]
        )
    with pytest.raises(errors.InvalidMedia):
        catalog.save_product(
            owner, title="Gloss", price_minor=100, photo_ids=[photo(owner, status="failed").pk]
        )
    with pytest.raises(errors.InvalidMedia):
        catalog.save_product(owner, title="Gloss", price_minor=100, video_id=photo(owner).pk)
    with pytest.raises(errors.NotAPro):
        catalog.save_product(buyer(), title="Gloss", price_minor=100)


def test_only_her_own_products():
    item = product(publish=False)
    other = shop_owner("Inès Ongles")
    with pytest.raises(errors.ProductNotFound):
        catalog.save_product(other, product=item, title="X", price_minor=1)
    with pytest.raises(errors.ProductNotFound):
        catalog.publish(other, item)
    with pytest.raises(errors.ProductNotFound):
        catalog.pause(other, item)
    with pytest.raises(errors.ProductNotFound):
        catalog.archive(other, item)
    with pytest.raises(errors.ProductNotFound):
        catalog.set_stock(other, item.variants.first().pk, 3)


def test_publishing_needs_everything():
    owner = shop_owner()
    bare = catalog.save_product(owner, title="Gloss", price_minor=1_000, variants=[{"stock": 1}])
    with pytest.raises(errors.IncompleteProduct):
        catalog.publish(owner, bare)
    unverified = shop_owner("Fifi Mode", verification_status=ProProfile.Verification.NONE)
    item = product(unverified, publish=False)
    with pytest.raises(errors.VerificationNeeded):
        catalog.publish(unverified, item)
    published = product(owner)
    with pytest.raises(errors.InvalidStep):
        catalog.publish(owner, published)


def test_the_shop_switch_off_blocks_publishing():
    from apps.core.models import FeatureFlag

    FeatureFlag.objects.filter(key="shop").update(is_enabled=False)
    owner = shop_owner()
    with pytest.raises(errors.ShopUnavailable):
        product(owner)


def test_a_forbidden_substance_is_blocked_before_publication():
    owner = shop_owner()
    item = product(owner, title="Crème Hydro-Quinone 4 %", publish=False)
    with pytest.raises(errors.ForbiddenProduct) as caught:
        catalog.publish(owner, item)
    assert "hydroquinone" in caught.value.text() and "ABMed" in caught.value.text()
    item.refresh_from_db()
    assert item.status == P.DRAFT and item.matched_terms == ["hydroquinone"]


def test_a_doubtful_product_waits_for_the_team_then_is_approved():
    owner = shop_owner()
    item = product(owner, title="Lait éclaircissant au karité")
    assert item.status == P.IN_REVIEW and item.matched_terms == ["eclaircissant"]
    assert "éclaircissant" in item.review_reason
    with pytest.raises(errors.InvalidStep):
        catalog.publish(owner, item)
    catalog.approve(item, actor=buyer("Solange"))
    item.refresh_from_db()
    assert item.status == P.PUBLISHED and item.review_reason == ""
    assert Notification.objects.filter(user=owner, event_key="shop.product_approved").exists()
    with pytest.raises(errors.InvalidStep):
        catalog.approve(item, actor=None)


def test_refused_then_unblocked():
    owner = shop_owner()
    item = product(owner, title="Gloss Miel")
    client = buyer()
    cart.add(client, variant_id=item.variants.first().pk)
    catalog.refuse(item, actor=None, reason="Photo d'un autre site")
    item.refresh_from_db()
    assert item.status == P.BLOCKED and not CartItem.objects.exists()
    assert Notification.objects.filter(user=owner, event_key="shop.product_refused").exists()
    with pytest.raises(errors.InvalidStep):
        catalog.publish(owner, item)
    catalog.unblock(item, actor=None)
    item.refresh_from_db()
    assert item.status == P.DRAFT
    with pytest.raises(errors.InvalidStep):
        catalog.unblock(item, actor=None)
    catalog.archive(owner, item)
    with pytest.raises(errors.InvalidStep):
        catalog.refuse(item, actor=None)


def test_changing_a_product_online_checks_it_again():
    owner = shop_owner()
    item = product(owner)
    with pytest.raises(errors.ForbiddenProduct):
        catalog.save_product(
            owner, product=item, title="Fond de teint au mercure", price_minor=8_000
        )
    item.refresh_from_db()
    assert item.title == "Fond de teint Velours"  # nothing was saved
    catalog.save_product(owner, product=item, title="Fond de teint blanchissant", price_minor=8_000)
    item.refresh_from_db()
    assert item.status == P.IN_REVIEW


def test_moderation_sees_the_product():
    PlatformSettingFactory(key="moderation.blocked_words", value='["arnaque"]', value_type="json")
    item = product(description="Ce n'est pas une arnaque")
    assert item.visibility == "held"
    assert ModerationCase.objects.filter(target_id=item.pk).exists()


def test_words_found_with_dots_dashes_and_the_old_setting():
    ForbiddenTerm.objects.create(term="Acide Glycolique", action="review", reason="Test")
    PlatformSettingFactory(
        key="moderation.banned_product_words", value='["fake"]', value_type="json"
    )
    finding = forbidden.check_text("Sérum H.Y.D.R.O.Q.U.I.N.O.N.E et acide glycolique, fake")
    assert finding.blocked == ["hydroquinone"]
    assert finding.review == ["Acide Glycolique", "fake"]
    assert forbidden.check_text("Faux cils fakeeyelashes").terms == []
    assert str(ForbiddenTerm.objects.get(term="mercure")) == "mercure"


def test_pause_archive_and_quick_stock():
    owner = shop_owner()
    item = product(owner, stock=0)
    variant = item.variants.get()
    catalog.pause(owner, item)
    with pytest.raises(errors.InvalidStep):
        catalog.pause(owner, item)
    catalog.publish(owner, item)
    assert catalog.set_stock(owner, variant.pk, 7).stock == 7
    with pytest.raises(errors.InvalidVariants):
        catalog.set_stock(owner, variant.pk, -2)
    catalog.archive(owner, item)
    item.refresh_from_db()
    assert item.status == P.ARCHIVED and item.archived_at
    with pytest.raises(errors.ProductNotFound):
        catalog.set_stock(owner, variant.pk, 1)
    with pytest.raises(errors.ProductNotFound):
        catalog.save_product(owner, product=item, title="X", price_minor=1)
    with pytest.raises(errors.ProductNotFound):
        catalog.publish(owner, item)


def test_a_variant_left_out_is_switched_off():
    owner = shop_owner()
    item = product(owner, variants=[{"size": "S", "stock": 2}, {"size": "M", "stock": 2}])
    small, medium = item.variants.order_by("position")
    client = buyer()
    cart.add(client, variant_id=medium.pk)
    catalog.save_product(
        owner,
        product=item,
        title=item.title,
        price_minor=8_000,
        category_key="makeup",
        variants=[{"id": str(small.pk), "size": "S", "stock": 5}, {"size": "L", "stock": 1}],
    )
    medium.refresh_from_db()
    assert not medium.is_active and not CartItem.objects.exists()
    assert Variant.objects.filter(product=item, is_active=True).count() == 2


def test_how_she_hands_over():
    owner = shop_owner()
    zone = delivers(owner, mode="partner", name="Calavi", fee=1_500)
    shop = ShopProfile.objects.get(pro__user=owner)
    assert shop.partner_delivery and shop.partner_name == "Gozem" and str(shop)
    assert str(zone) == "Calavi"
    changed = catalog.save_zone(owner, zone_id=zone.pk, mode="partner", name="Calavi", fee_minor=0)
    assert changed.fee_minor == 0
    for bad in ({"mode": "drone"}, {"name": " "}, {"fee_minor": -1}):
        with pytest.raises(errors.InvalidZone):
            catalog.save_zone(owner, **{"mode": "seller", "name": "Z", "fee_minor": 1, **bad})
    with pytest.raises(errors.InvalidZone):
        catalog.save_zone(
            shop_owner("Autre"), zone_id=zone.pk, mode="seller", name="Z", fee_minor=1
        )
    catalog.delete_zone(owner, zone.pk)
    with pytest.raises(errors.InvalidZone):
        catalog.delete_zone(owner, zone.pk)
    catalog.update_shop(owner, is_open=False, pickup_note="  Lundi au samedi  ")
    shop.refresh_from_db()
    assert not shop.is_open and shop.pickup_note == "Lundi au samedi"
