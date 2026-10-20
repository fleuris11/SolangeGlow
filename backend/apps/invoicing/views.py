from __future__ import annotations

from django.http import HttpResponse
from django.utils.translation import get_language
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttling import SettingRateThrottle
from apps.glowpro import selectors as glowpro
from apps.glowpro.models import Feature
from apps.pros.services import get_pro

from . import einvoice, pdf, services
from .models import Document, Issuer


def _iso(value):
    return value.isoformat() if value else None


def document_payload(document: Document) -> dict:
    return {
        "id": str(document.pk),
        "kind": document.kind,
        "number": document.number,
        "issued_at": _iso(document.issued_at),
        "buyer_name": document.buyer_name,
        "total_minor": document.total_minor,
        "tax_minor": document.tax_minor,
        "currency": document.currency,
        "paid_with": document.paid_with,
        "corrects": document.corrects.number if document.corrects_id else None,
        "cancelled": document.credit_notes.exists() if document.kind != "credit_note" else False,
        "einvoice_status": document.einvoice_status,
        "pdf_url": f"/api/v1/documents/{document.pk}.pdf",
    }


class DocumentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=Document.Kind.choices)
    number = serializers.CharField()
    issued_at = serializers.DateTimeField()
    buyer_name = serializers.CharField()
    total_minor = serializers.IntegerField()
    tax_minor = serializers.IntegerField()
    currency = serializers.CharField()
    paid_with = serializers.CharField(allow_blank=True)
    corrects = serializers.CharField(allow_null=True)
    cancelled = serializers.BooleanField()
    einvoice_status = serializers.ChoiceField(choices=Document.EInvoice.choices)
    pdf_url = serializers.CharField()


class DocumentListSerializer(serializers.Serializer):
    results = DocumentSerializer(many=True)
    einvoice_connected = serializers.BooleanField()
    can_send_electronic = serializers.BooleanField()


class BillingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Issuer
        fields = [
            "legal_name",
            "address",
            "registration",
            "vat_number",
            "vat_rate_bps",
            "vat_mention",
            "footer",
        ]
        extra_kwargs = {field: {"required": False} for field in fields}


class CreditInputSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=200)


class ProDocumentsView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SettingRateThrottle]
    throttle_scope = "salon"

    def get_throttles(self):
        return super().get_throttles() if self.request.method != "GET" else []

    def document(self, request, document_id) -> Document:
        pro = get_pro(request.user)
        found = Document.objects.filter(pk=document_id, issuer__pro=pro).first()
        if found is None:
            raise services.DocumentNotFound()
        return found


class BillingView(ProDocumentsView):
    """Her legal details printed on her invoices."""

    @extend_schema(tags=["invoicing"], responses=BillingSerializer)
    def get(self, request):
        return Response(BillingSerializer(services.issuer_for(get_pro(request.user))).data)

    @extend_schema(tags=["invoicing"], request=BillingSerializer, responses=BillingSerializer)
    def patch(self, request):
        data = BillingSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        issuer = services.update_issuer(get_pro(request.user), **data.validated_data)
        return Response(BillingSerializer(issuer).data)


class DocumentsView(ProDocumentsView):
    @extend_schema(
        tags=["invoicing"],
        parameters=[OpenApiParameter("kind", str, required=False)],
        responses=DocumentListSerializer,
    )
    def get(self, request):
        pro = get_pro(request.user)
        rows = Document.objects.filter(issuer__pro=pro).select_related("corrects")
        kind = request.query_params.get("kind")
        if kind in Document.Kind.values:
            rows = rows.filter(kind=kind)
        return Response(
            {
                "results": [document_payload(d) for d in rows.order_by("-issued_at")[:100]],
                "einvoice_connected": einvoice.is_connected(),
                "can_send_electronic": glowpro.has_feature(pro, Feature.EINVOICE),
            }
        )


class CreditView(ProDocumentsView):
    @extend_schema(tags=["invoicing"], request=CreditInputSerializer, responses=DocumentSerializer)
    def post(self, request, document_id):
        data = CreditInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        note = services.credit(
            self.document(request, document_id),
            actor=request.user,
            reason=data.validated_data["reason"],
        )
        return Response(document_payload(note))


class SendElectronicView(ProDocumentsView):
    @extend_schema(tags=["invoicing"], request=None, responses=DocumentSerializer)
    def post(self, request, document_id):
        document = self.document(request, document_id)
        glowpro.require(document.issuer.pro, Feature.EINVOICE)
        return Response(document_payload(services.send_electronic(document)))


class DocumentPdfView(APIView):
    """The PDF: for the pro who issued it, the client it was issued to, or the team."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["invoicing"], responses={(200, "application/pdf"): OpenApiTypes.BINARY})
    def get(self, request, document_id):
        document = (
            Document.objects.select_related("issuer__pro", "corrects")
            .filter(pk=document_id)
            .first()
        )
        user = request.user
        allowed = document is not None and (
            user.is_staff
            or document.buyer_user_id == user.pk
            or (document.issuer.pro_id and document.issuer.pro.user_id == user.pk)
        )
        if not allowed:
            raise services.DocumentNotFound()
        response = HttpResponse(
            pdf.render(document, get_language() or "fr"), content_type="application/pdf"
        )
        response["Content-Disposition"] = f'inline; filename="{document.number}.pdf"'
        response["Cache-Control"] = "private, max-age=3600"
        return response
