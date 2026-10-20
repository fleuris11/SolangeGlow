"""Packages of sessions and payments in several times (Premium « complete client file »).

The money paid online is held (secure payment) until the first session is done, then it
goes to the pro; installments paid after that go to her at once. A session is used by
itself when an appointment of the package's service is done.
"""

from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from apps.booking.models import Appointment, ClientRecord
from apps.core.audit.services import record
from apps.glowpro import selectors as glowpro
from apps.glowpro.models import Feature
from apps.notifications.services import notify
from apps.payments import services as payment_services
from apps.payments.models import Payment, Purpose
from apps.pros.models import Service

from .. import errors
from ..models import ClientPackage, Installment, InstallmentPlan, Package, PackageUse
from . import onsite

SOURCE = "salon_installment"
CP = ClientPackage.Status
I = Installment.Status  # noqa: E741
PS = Payment.Status


def add_months(day: datetime.date, months: int) -> datetime.date:
    import calendar

    month = day.month - 1 + months
    year, month = day.year + month // 12, month % 12 + 1
    return day.replace(
        year=year, month=month, day=min(day.day, calendar.monthrange(year, month)[1])
    )


@transaction.atomic
def save_package(pro, *, package_id=None, **values) -> Package:
    glowpro.require(pro, Feature.CLIENT_FILE)
    service = Service.objects.filter(pk=values.get("service_id"), pro=pro).first()
    name = (values.get("name") or "").strip()[:80]
    sessions = values.get("sessions")
    price = values.get("price_minor")
    if (
        service is None
        or not name
        or type(sessions) is not int
        or not 2 <= sessions <= 50
        or type(price) is not int
        or price <= 0
    ):
        raise errors.InvalidPackage()
    package = (
        Package.objects.filter(pk=package_id, pro=pro).first() if package_id else Package(pro=pro)
    )
    if package is None:
        raise errors.NotFound()
    package.service = service
    package.name = name
    package.sessions = sessions
    package.price_minor = price
    package.currency = service.currency
    package.validity_days = int(values.get("validity_days") or 365)
    package.max_installments = min(4, max(1, int(values.get("max_installments") or 1)))
    package.is_active = bool(values.get("is_active", True))
    package.full_clean(exclude=["pro", "service"])
    package.save()
    return package


def _schedule(total: int, count: int, first: datetime.date) -> list[tuple[datetime.date, int]]:
    """Equal parts, the rest of the division on the first one; one a month."""
    part, rest = divmod(total, count)
    return [(add_months(first, i), part + (rest if i == 0 else 0)) for i in range(count)]


def _start(package: Package, client_record: ClientRecord, installments: int, status: str):
    if not 1 <= installments <= package.max_installments:
        raise errors.InvalidInstallments(details={"max": package.max_installments})
    today = timezone.localdate()
    sold = ClientPackage.objects.create(
        package=package,
        pro=package.pro,
        record=client_record,
        client=client_record.client,
        sessions_total=package.sessions,
        price_minor=package.price_minor,
        currency=package.currency,
        expires_on=today + datetime.timedelta(days=package.validity_days),
        status=status,
    )
    plan = InstallmentPlan.objects.create(
        pro=package.pro,
        record=client_record,
        client_package=sold,
        label=package.name,
        total_minor=package.price_minor,
        currency=package.currency,
    )
    Installment.objects.bulk_create(
        Installment(plan=plan, position=i, due_on=due, amount_minor=amount)
        for i, (due, amount) in enumerate(_schedule(package.price_minor, installments, today))
    )
    return sold, plan


def _package(pro, package_id) -> Package:
    package = (
        Package.objects.select_related("service", "pro")
        .filter(pk=package_id, pro=pro, is_active=True)
        .first()
    )
    if package is None:
        raise errors.NotFound()
    return package


@transaction.atomic
def sell_on_site(
    pro, package_id, client_record: ClientRecord, *, installments: int = 1, method: str, actor
) -> ClientPackage:
    """Sold at the salon: the first payment is taken now (cash, MoMo…)."""
    glowpro.require(pro, Feature.CLIENT_FILE)
    package = _package(pro, package_id)
    sold, plan = _start(package, client_record, installments, CP.ACTIVE)
    first = plan.installments.order_by("position").first()
    record_on_site(first, method=method, actor=actor)
    record("salon.package_sold", sold, actor=actor)
    return sold


@transaction.atomic
def buy_online(user, pro, package_id, *, installments: int = 1) -> Payment:
    """The client buys a package on the showcase: the first payment, held until the first
    session."""
    from apps.booking.models import ClientRecord as Record

    glowpro.require(pro, Feature.CLIENT_FILE)
    package = _package(pro, package_id)
    client_record, _ = Record.objects.get_or_create(
        pro=pro, client=user, defaults={"name": user.first_name or str(user.phone or "")}
    )
    _sold, plan = _start(package, client_record, installments, CP.WAITING)
    first = plan.installments.order_by("position").first()
    return pay_online(first, user)


def pay_online(installment: Installment, user) -> Payment:
    installment = Installment.objects.select_related("plan__pro__user", "plan__client_package").get(
        pk=installment.pk
    )
    if installment.status != I.DUE:
        raise errors.InstallmentPaid()
    payment = installment.payment
    if payment is None or payment.status != PS.PENDING_PAYMENT:
        plan = installment.plan
        payment = payment_services.create_payment(
            user,
            plan.pro.user,
            purpose=Purpose.PACKAGE,
            items_minor=installment.amount_minor,
            currency=plan.currency,
            description=f"{plan.label} ({installment.position + 1})"[:200],
            delivery_mode=Payment.Delivery.SERVICE,
            source_type=SOURCE,
            source_id=installment.pk,
        )
        installment.payment = payment
        installment.save(update_fields=["payment", "updated_at"])
    return payment_services.start_checkout(payment, buyer=user)


@transaction.atomic
def record_on_site(installment: Installment, *, method: str, actor) -> Installment:
    installment = (
        Installment.objects.select_for_update(of=("self",))
        .select_related("plan__pro__country", "plan__record")
        .get(pk=installment.pk)
    )
    if installment.status != I.DUE:
        raise errors.InstallmentPaid()
    plan = installment.plan
    payment = onsite.record_payment(
        plan.pro,
        amount_minor=installment.amount_minor,
        method=method,
        actor=actor,
        label=f"{plan.label} ({installment.position + 1})",
        client_record=plan.record,
    )
    _mark_paid(installment, on_site=payment)
    return installment


def _mark_paid(installment: Installment, *, on_site=None) -> None:
    installment.status = I.PAID
    installment.paid_at = timezone.now()
    installment.on_site = on_site
    installment.save(update_fields=["status", "paid_at", "on_site", "updated_at"])
    plan = installment.plan
    if not plan.installments.filter(status=I.DUE).exists():
        plan.status = InstallmentPlan.Status.PAID
        plan.save(update_fields=["status", "updated_at"])
    sold = plan.client_package
    if sold is not None and sold.status == CP.WAITING:
        sold.status = CP.ACTIVE
        sold.save(update_fields=["status", "updated_at"])


def may_cancel_payment(payment: Payment, actor) -> bool:
    return True


def on_payment_change(payment: Payment) -> None:
    """Paid online: the installment is paid; held until the first session (else released)."""
    with transaction.atomic():
        installment = (
            Installment.objects.select_for_update(of=("self",))
            .select_related("plan__client_package")
            .filter(payment=payment)
            .first()
        )
        if installment is None:
            return
        if payment.status == PS.HELD and installment.status == I.DUE:
            _mark_paid(installment)
            sold = installment.plan.client_package
            if sold is None or sold.sessions_used > 0:
                payment_services.release(payment, reason="package_started")


def _release_held(sold: ClientPackage) -> None:
    for installment in Installment.objects.filter(
        plan__client_package=sold, payment__status=PS.HELD
    ).select_related("payment"):
        payment_services.release(installment.payment, reason="package_started")


@transaction.atomic
def use_session(
    sold: ClientPackage, *, appointment: Appointment | None = None, actor=None, note=""
):
    sold = ClientPackage.objects.select_for_update().get(pk=sold.pk)
    if sold.status != CP.ACTIVE or sold.sessions_left <= 0:
        raise errors.PackageUsedUp()
    PackageUse.objects.create(client_package=sold, appointment=appointment, note=note[:120])
    sold.sessions_used += 1
    if sold.sessions_left == 0:
        sold.status = CP.USED_UP
    sold.save(update_fields=["sessions_used", "status", "updated_at"])
    if sold.sessions_used == 1:
        _release_held(sold)
    record("salon.session_used", sold, actor=actor, metadata={"left": sold.sessions_left})
    if sold.client_id and sold.sessions_left == 1:
        transaction.on_commit(
            lambda: notify(
                sold.client,
                "salon.package_last_session",
                {"package": sold.package.name, "pro": sold.pro.display_name},
                link="/appointments",
            )
        )
    return sold


def on_completed(appointment: Appointment) -> None:
    """A done appointment uses a session of a running package of this service."""
    from apps.booking.services.agenda import record_for

    if hasattr(appointment, "package_use"):
        return
    client_record = record_for(appointment.pro, appointment)
    sold = (
        ClientPackage.objects.filter(
            record=client_record,
            package__service_id=appointment.service_id,
            status=CP.ACTIVE,
            expires_on__gte=timezone.localdate(),
        )
        .order_by("expires_on")
        .first()
    )
    if sold is not None:
        use_session(sold, appointment=appointment)


def remind_installments(today=None) -> int:
    """Two days before the date: the client is reminded (once)."""
    today = today or timezone.localdate()
    count = 0
    for installment in Installment.objects.filter(
        status=I.DUE,
        reminded_on__isnull=True,
        due_on__lte=today + datetime.timedelta(days=2),
        position__gt=0,
    ).select_related("plan__record__client", "plan__pro"):
        client = installment.plan.record.client
        installment.reminded_on = today
        installment.save(update_fields=["reminded_on", "updated_at"])
        if client is not None:
            notify(
                client,
                "salon.installment_due",
                {"label": installment.plan.label, "date": installment.due_on.isoformat()},
                link="/appointments",
            )
        count += 1
    return count


def expire_packages(today=None) -> int:
    today = today or timezone.localdate()
    return ClientPackage.objects.filter(status=CP.ACTIVE, expires_on__lt=today).update(
        status=CP.EXPIRED
    )
