"""Salon management: packages and installments, gift cards, stock, payments at the salon,
invoices. Premium features are refused on the free plan."""

import datetime

import pytest
from django.utils import timezone

from apps.booking.models import Appointment
from apps.booking.services import agenda, appointments
from apps.booking.tests.factories import at, salon, service
from apps.core.models import Country
from apps.core.tests.factories import CountryFactory, CurrencyFactory
from apps.glowpro import errors as glowpro_errors
from apps.glowpro.tests.factories import premium
from apps.invoicing.models import Document
from apps.messaging.tests.factories import adult
from apps.payments import services as payments
from apps.payments.models import Payment
from apps.salon import errors
from apps.salon.models import ClientPackage, GiftCard, Installment, StockMovement
from apps.salon.services import documents, giftcards, onsite, packages, stock
from apps.shop.tests.factories import product

pytestmark = pytest.mark.django_db
PS = Payment.Status


@pytest.fixture
def clock(monkeypatch):
    class Clock:
        value = at(8, day=datetime.date(2030, 1, 5))

        def set(self, moment):
            self.value = moment

    found = Clock()
    monkeypatch.setattr(timezone, "now", lambda: found.value)
    return found


def pay(payment: Payment) -> Payment:
    payments.mark_paid(
        payment, amount_minor=payment.total_minor, currency=payment.currency, key=str(payment.pk)
    )
    return Payment.objects.get(pk=payment.pk)


def done(pro, svc, client, clock, hour=10):
    booked = appointments.book(pro, svc.pk, at(hour), user=client)
    clock.set(at(hour + 2))
    appointments.complete(booked, actor=pro.user)
    clock.set(at(8, day=datetime.date(2030, 1, 5)))
    return Appointment.objects.get(pk=booked.pk)


# --- Packages -----------------------------------------------------------------------------------


def test_packages_are_premium():
    pro = salon()
    facial = service(pro, ("work", 60), name="Soin visage")
    with pytest.raises(glowpro_errors.PremiumRequired):
        packages.save_package(
            pro, service_id=facial.pk, name="5 soins", sessions=5, price_minor=50_000
        )


def test_a_package_bought_online_is_used_by_the_appointments(clock):
    pro = salon()
    premium(pro)
    facial = service(pro, ("work", 60), name="Soin visage", price=12_000)
    package = packages.save_package(
        pro,
        service_id=facial.pk,
        name="5 soins",
        sessions=5,
        price_minor=50_000,
        max_installments=2,
    )
    client = adult("Awa")
    payment = packages.buy_online(client, pro, package.pk, installments=2)
    assert payment.purpose == "package" and payment.items_minor == 25_000
    held = pay(payment)
    assert held.status == PS.HELD  # held until the first session
    sold = ClientPackage.objects.get(record__client=client)
    assert sold.status == ClientPackage.Status.ACTIVE and sold.sessions_left == 5
    done(pro, facial, client, clock)
    sold.refresh_from_db()
    assert sold.sessions_used == 1
    assert Payment.objects.get(pk=payment.pk).status == PS.RELEASED
    second = sold.installment_plan.installments.get(position=1)
    assert second.due_on == packages.add_months(timezone.localdate(), 1)
    paid = pay(packages.pay_online(second, client))
    assert paid.status == PS.RELEASED  # sessions started: no need to hold it
    sold.installment_plan.refresh_from_db()
    assert sold.installment_plan.status == "paid"


def test_a_package_sold_at_the_salon_and_used_by_hand():
    pro = salon()
    premium(pro)
    facial = service(pro, ("work", 60), name="Soin visage")
    package = packages.save_package(
        pro, service_id=facial.pk, name="2 soins", sessions=2, price_minor=20_000
    )
    booked = appointments.book(pro, facial.pk, at(10), user=adult("Awa"))
    record = agenda.record_for(pro, booked)
    sold = packages.sell_on_site(pro, package.pk, record, method="cash", actor=pro.user)
    assert sold.status == ClientPackage.Status.ACTIVE
    assert Installment.objects.get(plan__client_package=sold).on_site.method == "cash"
    packages.use_session(sold, actor=pro.user)
    sold = packages.use_session(sold, actor=pro.user)
    assert sold.status == ClientPackage.Status.USED_UP
    with pytest.raises(errors.PackageUsedUp):
        packages.use_session(sold)
    with pytest.raises(errors.InvalidInstallments):
        packages.sell_on_site(
            pro, package.pk, record, installments=3, method="cash", actor=pro.user
        )


# --- Gift cards ---------------------------------------------------------------------------------


def test_a_gift_card_bought_online_then_used_at_the_salon():
    pro = salon()
    buyer = adult("Grâce")
    card, payment = giftcards.buy_online(
        buyer, pro, amount_minor=30_000, recipient_name="Maman", recipient_contact="+2290197000077"
    )
    assert payment.purpose == "gift_card" and payment.commission_minor == 1_500  # 5 %
    assert pay(payment).status == PS.HELD
    card.refresh_from_db()
    assert card.status == GiftCard.Status.ACTIVE and len(card.code) == 10
    giftcards.redeem(pro, card.code.lower(), 10_000, actor=pro.user)
    card.refresh_from_db()
    assert card.balance_minor == 20_000
    assert Payment.objects.get(pk=payment.pk).status == PS.RELEASED  # first use: to the pro
    with pytest.raises(errors.NotEnoughBalance):
        giftcards.redeem(pro, card.code, 25_000)
    with pytest.raises(errors.GiftCardNotFound):
        giftcards.redeem(salon("Autre"), card.code, 1_000)  # only where it was sold
    with pytest.raises(errors.InvalidGiftCard):
        giftcards.buy_online(buyer, pro, amount_minor=100, recipient_name="Maman")


def test_a_gift_card_pays_a_booking_deposit():
    pro = salon()
    card = giftcards.sell_on_site(pro, amount_minor=10_000, method="cash", actor=pro.user)
    deposit = service(pro, ("work", 60), deposit_kind="amount", deposit_value=5_000)
    booked = appointments.book(
        pro,
        deposit.pk,
        at(10),
        guest_name="Inès",
        guest_phone="+2290197000001",
        gift_card_code=card.code,
    )
    assert booked.status == Appointment.Status.CONFIRMED and booked.payment_id is None
    card.refresh_from_db()
    assert card.balance_minor == 5_000
    from apps.booking import errors as booking_errors

    with pytest.raises(booking_errors.GiftCardRefused):
        appointments.book(pro, deposit.pk, at(14), user=adult(), gift_card_code="WRONGCODE1")


def test_an_unused_gift_card_expires_and_pays_the_pro(clock):
    pro = salon()
    card, payment = giftcards.buy_online(adult(), pro, amount_minor=20_000, recipient_name="Sika")
    pay(payment)
    clock.set(clock.value + datetime.timedelta(days=400))
    assert giftcards.expire() == 1
    card.refresh_from_db()
    assert card.status == GiftCard.Status.EXPIRED
    assert Payment.objects.get(pk=payment.pk).status == PS.RELEASED


# --- Stock --------------------------------------------------------------------------------------


def test_stock_with_barcodes_movements_and_alerts():
    pro = salon()
    with pytest.raises(glowpro_errors.PremiumRequired):
        stock.save_item(pro, name="Oxydant", kind="professional")
    premium(pro)
    oxidant = stock.save_item(
        pro, name="Oxydant 20 vol", kind="professional", unit="ml", ean="4006381333931",
        quantity=1000, alert_threshold=200,
    )  # fmt: skip
    assert oxidant.quantity == 1000 and stock.find_by_ean(pro, "4006381333931") == oxidant
    with pytest.raises(errors.InvalidStockItem):
        stock.save_item(pro, name="Faux", kind="retail", ean="4006381333932")  # wrong check digit
    with pytest.raises(errors.BarcodeTaken):
        stock.save_item(pro, name="Doublon", kind="retail", ean="4006381333931")
    stock.move(oxidant, -850, StockMovement.Kind.OUT, actor=pro.user)
    oxidant.refresh_from_db()
    assert oxidant.quantity == 150 and oxidant.alerted_on == timezone.localdate()
    assert pro.user.notifications.filter(event_key="salon.stock_low").count() == 1
    stock.move(oxidant, -10, StockMovement.Kind.LOSS)
    assert pro.user.notifications.filter(event_key="salon.stock_low").count() == 1  # once a day
    stock.count(oxidant, 120, actor=pro.user)
    assert oxidant.movements.first().kind == "inventory" and oxidant.movements.first().change == -20


def test_a_done_service_uses_its_products(clock):
    pro = salon()
    premium(pro)
    colour = service(pro, ("work", 30), ("wait", 30), name="Coloration")
    tube = stock.save_item(pro, name="Tube 6.0", kind="professional", quantity=10)
    oxidant = stock.save_item(pro, name="Oxydant", kind="professional", unit="ml", quantity=500)
    stock.set_consumption(
        pro,
        colour.pk,
        [{"item_id": tube.pk, "quantity": 1}, {"item_id": oxidant.pk, "quantity": 60}],
    )
    appointment = done(pro, colour, adult("Awa"), clock)
    tube.refresh_from_db()
    oxidant.refresh_from_db()
    assert (tube.quantity, oxidant.quantity) == (9, 440)
    assert StockMovement.objects.filter(appointment=appointment, kind="use").count() == 2


def test_an_item_linked_to_the_shop_shares_its_stock():
    pro = salon(verification_status="verified")
    premium(pro)
    serum = product(pro.user, title="Sérum", stock=8)
    variant = serum.variants.get()
    item = stock.save_item(pro, name="Sérum", kind="retail", variant_id=variant.pk)
    assert item.quantity == 8
    stock.move(item, 5, StockMovement.Kind.IN)
    variant.refresh_from_db()
    assert variant.stock == 13


# --- Payments at the salon and invoices ---------------------------------------------------------


def test_cash_is_recorded_in_benin_only():
    pro = salon()
    assert onsite.methods_for(pro) == ["cash", "momo"]
    paid = onsite.record_payment(
        pro, amount_minor=15_000, method="momo", actor=pro.user, reference="MTN-123"
    )
    receipt = documents.for_on_site(paid)
    assert receipt.kind == Document.Kind.RECEIPT and receipt.total_minor == 15_000
    assert "Mobile Money" in receipt.paid_with
    onsite.cancel_payment(paid, actor=pro.user, reason="Erreur")
    assert Document.objects.filter(corrects=receipt, kind="credit_note").exists()
    with pytest.raises(errors.AlreadyCancelled):
        onsite.cancel_payment(paid, actor=pro.user, reason="Encore")
    with pytest.raises(errors.TerminalNotConfigured):
        onsite.record_payment(pro, amount_minor=1_000, method="card", actor=pro.user)
    euro = CurrencyFactory(code="EUR", name="Euro", symbol="€", decimal_places=2)
    france = CountryFactory(
        code="FR", name="France", phone_prefix="+33", timezone="Europe/Paris", default_currency=euro
    )
    paris = salon("Salon Paris", country=france, currency="EUR")
    assert onsite.methods_for(paris) == []
    with pytest.raises(errors.MethodNotAvailable):
        onsite.record_payment(paris, amount_minor=2_500, method="cash", actor=paris.user)
    assert Country.objects.filter(code="FR").exists()


def test_the_invoice_of_a_done_appointment(clock):
    pro = salon()
    svc = service(pro, ("work", 60), name="Tresses", price=18_000)
    appointment = done(pro, svc, adult("Awa"), clock)
    onsite.record_payment(
        pro, amount_minor=18_000, method="cash", actor=pro.user, appointment=appointment
    )
    invoice = documents.for_appointment(appointment)
    assert invoice.kind == Document.Kind.INVOICE and invoice.total_minor == 18_000
    assert invoice.buyer_name == "Awa" and invoice.paid_with
    assert documents.for_appointment(appointment) == invoice  # once
