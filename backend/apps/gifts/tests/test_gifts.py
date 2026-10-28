"""Diaspora gifts: euros paid in France, a service, a product or a Glow gift card used in
FCFA in Benin, refunds back onto the gift, sending on the chosen day, proof of joy."""

import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.booking.models import Appointment, AppointmentPhoto
from apps.booking.services import appointments
from apps.booking.tests.factories import NOW, at, salon, service
from apps.core.tests.factories import CountryFactory, CurrencyFactory
from apps.gifts import errors, selectors, services
from apps.gifts.models import Gift, GiftUse
from apps.gifts.services import common
from apps.messaging.tests.factories import adult, minor, upload
from apps.notifications.models import ContactMessage
from apps.payments import ledger
from apps.payments import services as payment_services
from apps.payments.models import LedgerAccount, Payment
from apps.selection_france.models import SelectionOrder
from apps.selection_france.tests import factories as selection
from apps.shop import errors as shop_errors
from apps.shop.models import Order
from apps.shop.tests import factories as shop

pytestmark = pytest.mark.django_db
G = Gift.Status
PS = Payment.Status
MAMAN = "+2290197000777"


@pytest.fixture
def clock(monkeypatch):
    class Clock:
        value = NOW

        def set(self, moment):
            self.value = moment

    found = Clock()
    monkeypatch.setattr(timezone, "now", lambda: found.value)
    return found


@pytest.fixture
def france():
    return CountryFactory(
        code="FR",
        name="France",
        phone_prefix="+33",
        timezone="Europe/Paris",
        default_currency=CurrencyFactory(code="EUR", name="Euro", symbol="€", decimal_places=2),
    )


@pytest.fixture
def giver(france):
    return adult("Grâce", country=france, phone="+33612345678")


def paid(gift: Gift) -> Gift:
    payment = Payment.objects.get(pk=gift.payment_id)
    payment_services.mark_paid(
        payment, amount_minor=payment.total_minor, currency="EUR", key=f"t:{payment.pk}"
    )
    gift.refresh_from_db()
    return gift


def offer(giver, kind=Gift.Kind.SERVICE, **kwargs) -> Gift:
    targets = {
        k: kwargs.pop(k)
        for k in list(kwargs)
        if k
        in (
            "service_id",
            "variant_id",
            "delivery_mode",
            "zone_id",
            "selection_product_id",
            "option",
            "amount_minor",
        )
    }
    kwargs.setdefault("recipient_name", "Maman Pélagie")
    kwargs.setdefault("recipient_phone", MAMAN)
    return services.offer(giver, services.quote(kind, **targets), **kwargs)


# --- Money ----------------------------------------------------------------------------------------


def test_euros_and_fcfa_at_the_fixed_rate():
    rate = Decimal("655.957")
    assert common.eur_for(15_000, rate) == 2_287  # 22.87 € pays at least 15 000 FCFA
    assert common.xof_for(2_287, rate) >= 15_000
    assert common.xof_for(5_000, rate) == 32_797  # 50 € → 32 797 FCFA (rounded down)
    assert common.eur_for(1, rate) == 1


def test_a_card_quote_has_limits_and_a_fee_of_six_percent(france):
    with pytest.raises(errors.InvalidAmount):
        services.quote(Gift.Kind.CARD, amount_minor=500)
    found = services.quote(Gift.Kind.CARD, amount_minor=5_000)
    assert found.value_minor == 32_797
    assert found.fee_minor == 300 and found.total_minor == 5_300


# --- An offered service -------------------------------------------------------------------------


def test_a_service_paid_in_euros_booked_by_a_guest_and_paid_to_the_pro_in_fcfa(clock, giver):
    pro = salon()
    braids = service(pro, ("work", 120), name="Tresses", price=15_000)
    gift = offer(giver, service_id=braids.pk, occasion="mothers_day", message="Bonne fête")
    assert gift.status == G.WAITING_PAYMENT and gift.value_minor == 15_000
    euros = gift.payment
    assert euros.currency == "EUR" and euros.items_minor == 2_287 and euros.buyer_fee_minor == 137
    gift = paid(gift)
    assert gift.status == G.SENT  # « now »: sent at once
    assert payment_services.receipt_code_for(gift.payment, giver) is None
    sent = ContactMessage.objects.get(phone=MAMAN, event_key="gifts.received")
    assert gift.token in sent.body and "Grâce" in sent.title

    # The giver's own look is a preview: not « opened ».
    services.open_gift(gift, giver)
    gift.refresh_from_db()
    assert gift.status == G.SENT
    gift = services.open_gift(gift)
    assert gift.status == G.OPENED and gift.opened_at

    booked = services.book(gift, at(10))
    assert booked.client is None and booked.client_phone == MAMAN
    assert booked.price_minor == booked.deposit_minor == 15_000
    xof = Payment.objects.get(pk=booked.payment_id)
    assert xof.provider == "gift" and xof.status == PS.HELD and xof.buyer_fee_minor == 0
    gift.refresh_from_db()
    assert gift.status == G.USED and gift.balance_minor == 0
    assert Payment.objects.get(pk=euros.pk).status == PS.RELEASED  # euros to the platform
    cash = ledger.account(LedgerAccount.Kind.PROVIDER_CASH, "XOF", provider="gift")
    assert ledger.balance(cash) == 15_000
    with pytest.raises(errors.AlreadyUsed):
        services.book(gift, at(14))

    booked.refresh_from_db()
    if booked.status == Appointment.Status.PENDING:
        appointments.confirm(booked, actor=pro.user)
    clock.set(at(13))
    appointments.complete(Appointment.objects.get(pk=booked.pk), actor=pro.user)
    assert Payment.objects.get(pk=xof.pk).status == PS.RELEASED  # the pro is paid in FCFA
    gift.refresh_from_db()
    assert gift.proof_asked_at is not None


def test_a_refused_booking_gives_the_money_back_to_the_gift(clock, giver):
    pro = salon()
    braids = service(pro, ("work", 60), name="Tresses", price=10_000)
    pro.booking_settings.auto_confirm = False
    pro.booking_settings.save()
    gift = services.open_gift(paid(offer(giver, service_id=braids.pk)))
    booked = services.book(gift, at(10), guest_name="Pélagie")
    assert booked.status == Appointment.Status.PENDING
    appointments.decline(booked, actor=pro.user)
    gift.refresh_from_db()
    assert gift.balance_minor == 10_000 and gift.status == G.OPENED
    use = GiftUse.objects.get(gift=gift)
    assert use.refunded_minor == 10_000 and use.credits.count() == 1
    again = services.book(gift, at(11))
    assert again.payment.status == PS.HELD


def test_the_giver_can_book_for_the_person(clock, giver):
    pro = salon()
    braids = service(pro, ("work", 60), price=10_000)
    gift = paid(offer(giver, service_id=braids.pk))
    booked = services.book(gift, at(10), viewer=giver)
    assert booked.client is None and booked.client_name == "Maman Pélagie"


def test_a_photo_goes_to_the_giver_only_with_a_yes(clock, giver):
    pro = salon()
    braids = service(pro, ("work", 60), price=10_000)
    gift = services.open_gift(paid(offer(giver, service_id=braids.pk)))
    booked = services.book(gift, at(10))
    photo = upload(pro.user, purpose="booking_result")
    AppointmentPhoto.objects.create(appointment=booked, media=photo)
    assert [m.pk for m, _source in services.candidates(gift)] == [photo.pk]
    with pytest.raises(errors.GiverCannotDoThis):
        services.answer(gift, photo.pk, send=True, viewer=giver)
    assert selectors.for_giver(gift)["proof"] is None
    services.answer(gift, photo.pk, send=True)
    gift.refresh_from_db()
    assert gift.proof_status == Gift.Proof.SENT and gift.proof_media_id == photo.pk
    assert selectors.for_giver(gift)["proof"]["id"] == str(photo.pk)
    with pytest.raises(errors.PhotoNotFound):
        services.answer(gift, upload(giver).pk, send=True)


# --- Sending, cancelling, expiring ---------------------------------------------------------------


def test_a_gift_waits_for_its_day(clock, giver):
    pro = salon()
    braids = service(pro, ("work", 60), price=10_000)
    gift = paid(offer(giver, service_id=braids.pk, send_at=NOW + datetime.timedelta(days=3)))
    assert gift.status == G.SCHEDULED
    assert selectors.reception(gift)["locked"] is True
    with pytest.raises(errors.NotOpenYet):
        services.book(gift, at(10, day=datetime.date(2030, 1, 10)))
    assert services.send_due() == 0
    clock.set(NOW + datetime.timedelta(days=3, minutes=1))
    assert services.send_due() == 1
    gift.refresh_from_db()
    assert gift.status == G.SENT
    with pytest.raises(errors.InvalidSendDate):
        offer(giver, service_id=braids.pk, send_at=NOW + datetime.timedelta(days=900))


def test_cancelled_while_unused_and_in_time_is_refunded_in_euros(clock, giver):
    pro = salon()
    braids = service(pro, ("work", 60), price=10_000)
    gift = paid(offer(giver, service_id=braids.pk))
    gift = services.cancel(gift, actor=giver)
    assert gift.status == G.REFUNDED
    assert Payment.objects.get(pk=gift.payment_id).status == PS.REFUNDED
    with pytest.raises(errors.GiftNotFound):
        services.book(gift, at(10))

    late = paid(offer(giver, service_id=braids.pk))
    clock.set(NOW + datetime.timedelta(days=15))
    with pytest.raises(errors.CannotCancel):
        services.cancel(late, actor=giver)
    with pytest.raises(errors.GiftNotFound):
        services.cancel(late, actor=adult("Autre"))


def test_a_used_gift_cannot_be_cancelled_and_expires_at_its_date(clock, giver):
    pro = salon()
    braids = service(pro, ("work", 60), price=10_000)
    gift = paid(offer(giver, service_id=braids.pk))
    services.book(gift, at(10))
    with pytest.raises(errors.CannotCancel):
        services.cancel(gift, actor=giver)
    unused = paid(offer(giver, service_id=braids.pk))
    clock.set(NOW + datetime.timedelta(days=400))
    assert services.expire() == 2
    unused.refresh_from_db()
    assert unused.status == G.EXPIRED
    assert Payment.objects.get(pk=unused.payment_id).status == PS.RELEASED


def test_one_reminder_for_a_forgotten_gift(clock, giver):
    pro = salon()
    braids = service(pro, ("work", 60), price=10_000)
    paid(offer(giver, service_id=braids.pk))
    clock.set(NOW + datetime.timedelta(days=31))
    assert services.remind() == 1
    assert services.remind() == 0
    assert ContactMessage.objects.filter(phone=MAMAN, event_key="gifts.reminder").count() == 1


def test_who_may_offer_and_to_whom(giver, france):
    pro = salon()
    braids = service(pro, ("work", 60), price=10_000)
    with pytest.raises(errors.CannotOffer):
        offer(minor("Lina"), service_id=braids.pk)
    with pytest.raises(errors.RecipientNeeded):
        offer(giver, service_id=braids.pk, recipient_phone="+33612345679")
    with pytest.raises(errors.OfferYourself):
        offer(pro.user, service_id=braids.pk)
    quoted = service(pro, ("work", 60), name="Sur devis", price=None, price_kind="quote")
    with pytest.raises(errors.NothingToOffer):
        services.quote(Gift.Kind.SERVICE, service_id=quoted.pk)


# --- An offered product -------------------------------------------------------------------------


def test_a_product_leaves_when_the_person_gives_her_address(giver):
    item = shop.product(price=8_000, stock=2)
    zone = shop.delivers(item.pro.user, fee=1_000)
    variant = item.variants.first()
    gift = offer(
        giver,
        Gift.Kind.PRODUCT,
        variant_id=variant.pk,
        delivery_mode="seller",
        zone_id=zone.pk,
    )
    assert gift.value_minor == 9_000 and gift.delivery_minor == 1_000
    gift = services.open_gift(paid(gift))
    with pytest.raises(shop_errors.AddressNeeded):
        services.receive(gift, address="")
    services.receive(gift, address="Rue 12, Akpakpa", landmarks="Près de l'église")
    order = Order.objects.get()
    assert order.buyer == giver and order.contact_phone == MAMAN
    assert order.payment.total_minor == 9_000 and order.payment.provider == "gift"
    assert order.payment.status == PS.HELD
    variant.refresh_from_db()
    assert variant.stock == 1
    page = selectors.reception(gift)
    assert page["uses"][0]["receipt_code"] and len(page["uses"][0]["receipt_code"]) == 6
    with pytest.raises(errors.AlreadyUsed):
        services.receive(gift, address="Ailleurs")


def test_an_unavailable_product_becomes_a_glow_card(giver):
    item = shop.product(price=8_000, stock=1)
    gift = services.open_gift(
        paid(
            offer(
                giver,
                Gift.Kind.PRODUCT,
                variant_id=item.variants.first().pk,
                delivery_mode="pickup",
            )
        )
    )
    with pytest.raises(errors.GiverCannotDoThis):
        services.as_card(gift, viewer=giver)
    gift = services.as_card(gift)
    assert gift.kind == Gift.Kind.CARD and gift.balance_minor == 8_000


def test_a_france_selection_product_is_collected_at_a_pick_up_point(giver):
    item = selection.product()
    point = selection.point()
    gift = services.open_gift(paid(offer(giver, Gift.Kind.SELECTION, selection_product_id=item.pk)))
    assert gift.value_minor == item.price_xof
    services.receive(gift, pickup_point_id=point.pk)
    placed = SelectionOrder.objects.get()
    assert placed.pickup_point == point and placed.payment.provider == "gift"
    assert placed.status == SelectionOrder.Status.TO_ORDER


# --- The Glow gift card -------------------------------------------------------------------------


def test_a_glow_card_pays_several_purchases_until_nothing_is_left(giver):
    card = paid(offer(giver, Gift.Kind.CARD, amount_minor=2_000))  # 13 119 FCFA
    assert card.value_minor == 13_119
    awa = adult("Awa", phone=MAMAN)
    item = shop.product(price=8_000)
    first = shop.order(awa, item, paid=False)
    card = services.pay_with_card(card.code.lower(), user=awa, group_id=first.payment.group_id)
    first.refresh_from_db()
    assert first.payment.status == PS.HELD and first.payment.provider == "gift"
    assert card.balance_minor == 13_119 - first.payment.total_minor
    assert card.recipient_user == awa
    second = shop.order(awa, item, paid=False)
    with pytest.raises(errors.NotEnoughLeft):
        services.pay_with_card(card.code, user=awa, group_id=second.payment.group_id)
    with pytest.raises(errors.GiftNotFound):
        services.pay_with_card("WRONG", user=awa, group_id=second.payment.group_id)
    with pytest.raises(errors.GiftNotFound):
        services.pay_with_card(card.code, user=giver, group_id=second.payment.group_id)
    assert [g.pk for g in selectors.received_by(awa)] == [card.pk]


def test_a_glow_card_pays_a_booking_deposit(clock, giver):
    card = paid(offer(giver, Gift.Kind.CARD, amount_minor=2_000))
    pro = salon()
    braids = service(pro, ("work", 60), price=10_000, deposit_kind="amount", deposit_value=3_000)
    awa = adult("Awa")
    booked = appointments.book(pro, braids.pk, at(10), user=awa, gift_card_code=card.code)
    assert booked.status != Appointment.Status.AWAITING_DEPOSIT
    assert booked.payment.provider == "gift" and booked.payment.status == PS.HELD
    card.refresh_from_db()
    assert card.balance_minor == 13_119 - booked.payment.total_minor


def test_a_glow_card_pays_a_single_payment_in_fcfa_only(giver, france):
    card = paid(offer(giver, Gift.Kind.CARD, amount_minor=5_000))
    awa = adult("Awa")
    placed = selection.order(awa, paid=False)
    services.pay_with_card(card.code, user=awa, payment_id=placed.payment_id)
    placed.refresh_from_db()
    assert placed.payment.status == PS.HELD
    other = paid(offer(giver, Gift.Kind.CARD, amount_minor=2_000))
    euros = other.payment  # already paid: not pending
    with pytest.raises(errors.GiftNotFound):
        services.pay_with_card(card.code, user=giver, payment_id=euros.pk)


def test_the_platform_sees_what_gifts_paid_in_fcfa(clock, giver):
    pro = salon()
    braids = service(pro, ("work", 60), price=10_000)
    gift = paid(offer(giver, service_id=braids.pk))
    services.book(gift, at(10))
    assert selectors.owed() == {"xof_minor": 10_000, "count": 1}
