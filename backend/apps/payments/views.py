from __future__ import annotations

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import exceptions, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttling import SettingRateThrottle
from apps.core.selectors import get_setting
from apps.pros.models import ProProfile

from . import errors, selectors, services
from . import serializers as s
from .models import Dispute, LedgerAccount, Payment, PayoutMethod, SellerTaxProfile
from .providers import EventKind, InvalidSignature, ProviderNotConfigured
from .services import webhooks
from .services.common import S


def _payment(request, payment_id) -> Payment:
    payment = selectors.payment_for(request.user, payment_id)
    if payment is None:
        raise errors.PaymentNotFound()
    return payment


def _answer(request, payment_id, code=status.HTTP_200_OK) -> Response:
    return Response(s.payment_payload(_payment(request, payment_id), request.user), status=code)


class PaymentsView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "payments"

    def get_throttles(self):
        return super().get_throttles() if self.request.method != "GET" else []


class PaymentListView(PaymentsView):
    """Her purchases, or (role=seller) her sales: newest first."""

    @extend_schema(
        tags=["payments"],
        operation_id="payments_list",
        parameters=[OpenApiParameter("role", str, enum=["buyer", "seller"], required=False)],
        responses=s.PaymentListSerializer,
    )
    def get(self, request):
        role = "seller" if request.query_params.get("role") == "seller" else "buyer"
        rows = selectors.payments_of(request.user, role=role)[:50]
        return Response({"results": [s.payment_payload(p, request.user) for p in rows]})


class PaymentView(PaymentsView):
    @extend_schema(tags=["payments"], responses=s.PaymentSerializer)
    def get(self, request, payment_id):
        return _answer(request, payment_id)


class CheckoutView(PaymentsView):
    """The provider's payment page (the test page in development)."""

    @extend_schema(tags=["payments"], request=None, responses=s.PaymentSerializer)
    def post(self, request, payment_id):
        services.start_checkout(_payment(request, payment_id), buyer=request.user)
        return _answer(request, payment_id)


class TestOutcomeView(PaymentsView):
    """Test provider only: success, failure or giving up, answered by a signed webhook."""

    @extend_schema(
        tags=["payments"], request=s.TestOutcomeSerializer, responses=s.PaymentSerializer
    )
    def post(self, request, payment_id):
        payment = _payment(request, payment_id)
        if not settings.PAYMENTS_FAKE_ENABLED or payment.provider != "fake":
            raise exceptions.NotFound()
        if payment.buyer_id != request.user.pk or payment.status != S.PENDING_PAYMENT:
            raise errors.InvalidTransition()
        data = s.TestOutcomeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        if not payment.provider_reference:
            services.start_checkout(payment, buyer=request.user)
        kind = {
            "succeeded": EventKind.PAYMENT_SUCCEEDED,
            "failed": EventKind.PAYMENT_FAILED,
            "abandoned": EventKind.PAYMENT_CANCELLED,
        }[data.validated_data["outcome"]]
        from .tasks import send_fake_event

        send_fake_event.delay(
            kind, payment.provider_reference, payment.total_minor, payment.currency
        )
        return _answer(request, payment_id)


def _group(request, group_id):
    group = selectors.group_for(request.user, group_id)
    if group is None:
        raise errors.PaymentNotFound()
    return group


class GroupView(PaymentsView):
    """A cart paid in one go: its orders' payments and whether the provider answered."""

    @extend_schema(tags=["payments"], responses=s.PaymentGroupSerializer)
    def get(self, request, group_id):
        return Response(s.group_payload(_group(request, group_id), request.user))


class GroupCheckoutView(PaymentsView):
    @extend_schema(tags=["payments"], request=None, responses=s.PaymentGroupSerializer)
    def post(self, request, group_id):
        group = services.start_group_checkout(_group(request, group_id), buyer=request.user)
        return Response(s.group_payload(group, request.user))


class GroupTestOutcomeView(PaymentsView):
    """Test provider only: the answer for a whole cart."""

    @extend_schema(
        tags=["payments"], request=s.TestOutcomeSerializer, responses=s.PaymentGroupSerializer
    )
    def post(self, request, group_id):
        group = _group(request, group_id)
        if not settings.PAYMENTS_FAKE_ENABLED or group.provider != "fake":
            raise exceptions.NotFound()
        data = s.TestOutcomeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        group = services.start_group_checkout(group, buyer=request.user)
        kind = {
            "succeeded": EventKind.PAYMENT_SUCCEEDED,
            "failed": EventKind.PAYMENT_FAILED,
            "abandoned": EventKind.PAYMENT_CANCELLED,
        }[data.validated_data["outcome"]]
        from .tasks import send_fake_event

        send_fake_event.delay(kind, group.provider_reference, group.total_minor, group.currency)
        group.refresh_from_db()
        return Response(s.group_payload(group, request.user))


class ShipView(PaymentsView):
    @extend_schema(tags=["payments"], request=s.ShipSerializer, responses=s.PaymentSerializer)
    def post(self, request, payment_id):
        data = s.ShipSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.ship(_payment(request, payment_id), actor=request.user, **data.validated_data)
        return _answer(request, payment_id)


class DeliveredView(PaymentsView):
    @extend_schema(tags=["payments"], request=s.DeliveredSerializer, responses=s.PaymentSerializer)
    def post(self, request, payment_id):
        data = s.DeliveredSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.mark_delivered(
            _payment(request, payment_id),
            actor=request.user,
            proof_media_id=data.validated_data["proof_media_id"],
        )
        return _answer(request, payment_id)


class ConfirmView(PaymentsView):
    """The seller types the code the client gives her at the handover."""

    throttle_scope = "receipt_code"

    @extend_schema(tags=["payments"], request=s.CodeSerializer, responses=s.PaymentSerializer)
    def post(self, request, payment_id):
        data = s.CodeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.confirm_receipt(
            _payment(request, payment_id), data.validated_data["code"], actor=request.user
        )
        return _answer(request, payment_id)


class CourierLinkView(PaymentsView):
    @extend_schema(tags=["payments"], request=None, responses=s.CourierLinkSerializer)
    def post(self, request, payment_id):
        token = services.courier_token(_payment(request, payment_id), seller=request.user)
        return Response({"url": f"{settings.SITE_URL}/courier/{token}"})


class CourierView(APIView):
    """For the courier, without account: see the order and type the code."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "receipt_code"

    def get_throttles(self):
        return super().get_throttles() if self.request.method != "GET" else []

    @extend_schema(tags=["payments"], responses=s.CourierPaymentSerializer)
    def get(self, request, token):
        payment = services.payment_for_courier(token)
        from apps.messaging.payloads import person_payload

        return Response(
            {
                "reference": payment.reference,
                "description": payment.description,
                "seller": person_payload(payment.seller)["name"],
            }
        )

    @extend_schema(tags=["payments"], request=s.CodeSerializer, responses={204: None})
    def post(self, request, token):
        data = s.CodeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.confirm_receipt(services.payment_for_courier(token), data.validated_data["code"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class CancelView(PaymentsView):
    @extend_schema(tags=["payments"], request=None, responses=s.PaymentSerializer)
    def post(self, request, payment_id):
        services.cancel(_payment(request, payment_id), actor=request.user)
        return _answer(request, payment_id)


class NewCodeView(PaymentsView):
    @extend_schema(tags=["payments"], request=None, responses=s.PaymentSerializer)
    def post(self, request, payment_id):
        services.renew_receipt_code(_payment(request, payment_id), buyer=request.user)
        return _answer(request, payment_id)


class DisputeView(PaymentsView):
    @extend_schema(
        tags=["payments"], request=s.OpenDisputeSerializer, responses={201: s.PaymentSerializer}
    )
    def post(self, request, payment_id):
        data = s.OpenDisputeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        services.open_dispute(
            _payment(request, payment_id),
            by=request.user,
            reason=values["reason"],
            description=values.get("description", ""),
            media_ids=values.get("media_ids", []),
        )
        return _answer(request, payment_id, status.HTTP_201_CREATED)


class EvidenceView(PaymentsView):
    @extend_schema(
        tags=["payments"], request=s.EvidenceCreateSerializer, responses=s.PaymentSerializer
    )
    def post(self, request, payment_id):
        payment = _payment(request, payment_id)
        dispute = Dispute.objects.filter(payment=payment).first()
        if dispute is None:
            raise errors.DisputeNotAllowed()
        data = s.EvidenceCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.add_evidence(
            dispute,
            author=request.user,
            text=data.validated_data.get("text", ""),
            media_id=data.validated_data.get("media_id"),
        )
        return _answer(request, payment_id)


@extend_schema(exclude=True)  # called by the providers, not by the apps
class WebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    def post(self, request, provider):
        try:
            webhooks.handle(provider, request.headers, request.body)
        except ProviderNotConfigured as exc:
            raise exceptions.NotFound() from exc
        except (InvalidSignature, ValueError, KeyError) as exc:
            raise exceptions.ValidationError({"signature": "refused"}) from exc
        return Response({"received": True})


webhook_view = csrf_exempt(WebhookView.as_view())


# --- Wallet of the seller ------------------------------------------------------------------------


def _minimum(currency: str) -> int:
    minimums = get_setting("payments.payout_minimum", default={"XOF": 5000, "EUR": 1000}) or {}
    return int(minimums.get(currency, 0))


class WalletView(PaymentsView):
    """Pending, available, being paid out, paid out; per currency."""

    @extend_schema(tags=["payments"], responses=s.WalletOverviewSerializer)
    def get(self, request):
        methods = {m.currency: m.display for m in PayoutMethod.objects.filter(seller=request.user)}
        currencies = selectors.currencies_of(request.user) or [_home_currency(request.user)]
        wallets = [
            {
                **selectors.wallet(request.user, currency),
                "minimum_minor": _minimum(currency),
                "payout_method": methods.get(currency),
            }
            for currency in currencies
        ]
        payouts = request.user.payouts.order_by("-created_at")[:20]
        return Response(
            {
                "wallets": wallets,
                "payouts": [
                    {
                        "id": str(p.pk),
                        "amount_minor": p.amount_minor,
                        "currency": p.currency,
                        "status": p.status,
                        "destination": p.destination,
                        "created_at": p.created_at.isoformat(),
                        "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                    }
                    for p in payouts
                ],
            }
        )


def _home_currency(user) -> str:
    pro = ProProfile.objects.filter(user=user).first()
    if pro and pro.currency:
        return pro.currency
    return user.preferred_currency or "XOF"


class WalletHistoryView(PaymentsView):
    @extend_schema(
        tags=["payments"],
        parameters=[OpenApiParameter("currency", str, required=True)],
        responses=s.WalletLineSerializer(many=True),
    )
    def get(self, request):
        currency = (request.query_params.get("currency") or "XOF").upper()
        rows = []
        for line in selectors.wallet_history(request.user, currency):
            payment = line.entry.payment
            rows.append(
                {
                    "id": line.id,
                    "created_at": line.entry.created_at.isoformat(),
                    "kind": line.entry.kind,
                    "account": "pending"
                    if line.account.kind == LedgerAccount.Kind.SELLER_PENDING
                    else "available",
                    "amount_minor": line.credit_minor - line.debit_minor,
                    "reference": payment.reference if payment else None,
                    "payment_id": str(payment.pk) if payment else None,
                }
            )
        return Response(rows)


class PayoutRequestView(PaymentsView):
    @extend_schema(
        tags=["payments"], request=s.PayoutRequestSerializer, responses={201: s.PayoutSerializer}
    )
    def post(self, request):
        data = s.PayoutRequestSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        payout = services.request_payout(request.user, **data.validated_data)
        payout.refresh_from_db()
        return Response(
            {
                "id": str(payout.pk),
                "amount_minor": payout.amount_minor,
                "currency": payout.currency,
                "status": payout.status,
                "destination": payout.destination,
                "created_at": payout.created_at.isoformat(),
                "paid_at": payout.paid_at.isoformat() if payout.paid_at else None,
            },
            status=status.HTTP_201_CREATED,
        )


class PayoutMethodsView(PaymentsView):
    @extend_schema(tags=["payments"], responses=s.PayoutMethodShownSerializer(many=True))
    def get(self, request):
        return Response(
            [
                {"currency": m.currency, "kind": m.kind, "display": m.display}
                for m in PayoutMethod.objects.filter(seller=request.user)
            ]
        )

    @extend_schema(
        tags=["payments"], request=s.PayoutMethodSerializer, responses=s.PayoutMethodShownSerializer
    )
    def put(self, request):
        data = s.PayoutMethodSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = dict(data.validated_data)
        currency, kind = values.pop("currency"), values.pop("kind")
        if kind == PayoutMethod.Kind.FAKE and not settings.PAYMENTS_FAKE_ENABLED:
            raise exceptions.ValidationError({"kind": "unavailable"})
        method = services.save_payout_method(
            request.user, currency=currency, kind=kind, details=values
        )
        return Response(
            {"currency": method.currency, "kind": method.kind, "display": method.display}
        )


class TaxProfileView(PaymentsView):
    """What a platform declares about its sellers (DAC7). The tax number never comes back."""

    @extend_schema(tags=["payments"], responses=s.TaxProfileSerializer)
    def get(self, request):
        profile = SellerTaxProfile.objects.filter(seller=request.user).first()
        if profile is None:
            raise exceptions.NotFound()
        return Response(s.TaxProfileSerializer(profile).data)

    @extend_schema(
        tags=["payments"], request=s.TaxProfileSerializer, responses=s.TaxProfileSerializer
    )
    def put(self, request):
        data = s.TaxProfileSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        profile = services.save_tax_profile(request.user, **data.validated_data)
        return Response(s.TaxProfileSerializer(profile).data)


class DemoPaymentView(PaymentsView):
    """Development only (never routed in production): a pretend order to try the flow."""

    @extend_schema(exclude=True)
    def post(self, request):
        data = s.DemoPaymentSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        pro = ProProfile.objects.filter(slug=values["seller_slug"]).select_related("user").first()
        if pro is None:
            raise exceptions.NotFound()
        payment = services.create_payment(
            request.user,
            pro.user,
            purpose="order",
            items_minor=values["items_minor"],
            delivery_minor=values.get("delivery_minor", 0),
            currency=pro.currency,
            description=values["description"],
            delivery_mode=values.get("delivery_mode", Payment.Delivery.SELLER),
            source_type="demo",
        )
        services.start_checkout(payment, buyer=request.user)
        return Response(s.payment_payload(payment, request.user), status=status.HTTP_201_CREATED)
