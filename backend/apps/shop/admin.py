"""Shops in the back office: products to check (accept or refuse in one click), forbidden
words, categories, orders (read only), promotions."""

from __future__ import annotations

from django import forms
from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TabbedTranslationAdmin
from unfold.admin import TabularInline
from unfold.decorators import action, display

from apps.core.audit.admin import AuditedModelAdmin
from apps.core.errors import DomainError
from apps.core.money import Money

from .models import (
    Bundle,
    BundleItem,
    Category,
    DeliveryZone,
    FlashSale,
    ForbiddenTerm,
    LivePin,
    Order,
    OrderLine,
    Product,
    ProductPhoto,
    PromoCode,
    SaleLive,
    ShopProfile,
    Variant,
)
from .services import catalog

STATUS_LABELS = {
    "draft": "info",
    "in_review": "warning",
    "published": "success",
    "paused": "info",
    "blocked": "danger",
    "archived": "danger",
}


def amount(value, currency) -> str:
    return Money(value or 0, currency).format("fr")


@admin.register(Category)
class CategoryAdmin(AuditedModelAdmin, TabbedTranslationAdmin):
    list_display = ["name", "key", "icon", "position", "is_active"]
    list_editable = ["position", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["key", "name"]


@admin.register(ForbiddenTerm)
class ForbiddenTermAdmin(AuditedModelAdmin):
    list_display = ["term", "action", "reason", "is_active"]
    list_editable = ["is_active"]
    list_filter = ["action", "is_active"]
    search_fields = ["term", "reason"]
    fields = ["term", "action", "reason", "is_active"]


class PhotoInline(TabularInline):
    model = ProductPhoto
    fields = ["preview", "position"]
    readonly_fields = ["preview", "position"]
    extra = 0
    tab = True

    def has_add_permission(self, request, obj=None):
        return False

    @display(description=_("photo"))
    def preview(self, photo):
        from apps.core.media.services import variant_url

        url = variant_url(photo.media, "thumb")
        return format_html('<img src="{}" width="80" height="80" alt="">', url) if url else "—"


class VariantInline(TabularInline):
    model = Variant
    fields = ["shade", "size", "color", "price_minor", "stock", "is_active"]
    readonly_fields = fields
    extra = 0
    tab = True

    def has_add_permission(self, request, obj=None):
        return False


class RefuseForm(forms.Form):
    reason = forms.CharField(
        label=_("Reason shown to the pro"), max_length=255, widget=forms.Textarea
    )


@admin.register(Product)
class ProductAdmin(AuditedModelAdmin):
    list_display = [
        "title",
        "pro",
        "category",
        "price",
        "status_badge",
        "visibility",
        "terms",
        "sold_count",
        "created_at",
    ]
    list_filter = ["status", "visibility", "category", "currency"]
    search_fields = ["title", "description", "pro__business_name", "pro__slug"]
    readonly_fields = [
        "pro",
        "slug",
        "currency",
        "status",
        "matched_terms",
        "review_reason",
        "published_at",
        "archived_at",
        "sold_count",
        "visibility",
    ]
    fields = [
        "pro",
        "title",
        "slug",
        "category",
        "description",
        "currency",
        "price_minor",
        "prep_days",
        "status",
        "visibility",
        "matched_terms",
        "review_reason",
        "published_at",
        "sold_count",
    ]
    inlines = [PhotoInline, VariantInline]
    actions_detail = ["approve_detail", "refuse_detail", "unblock_detail"]

    def has_add_permission(self, request):
        return False  # pros create their products

    def has_review_product_permission(self, request, object_id=None):
        return request.user.has_perm("shop.review_product")

    @display(description=_("price"))
    def price(self, product):
        return amount(product.price_minor, product.currency)

    @display(description=_("status"), ordering="status", label=STATUS_LABELS)
    def status_badge(self, product):
        return product.status, product.get_status_display()

    @display(description=_("forbidden words found"))
    def terms(self, product):
        return ", ".join(product.matched_terms) or "—"

    def _run(self, request, object_id, step, **kwargs):
        product = get_object_or_404(Product, pk=object_id)
        try:
            step(product, actor=request.user, **kwargs)
        except DomainError as exc:
            self.message_user(request, exc.text(), messages.ERROR)
        else:
            self.message_user(request, _("Done; the pro is told."), messages.SUCCESS)
        return redirect(reverse("admin:shop_product_change", args=[object_id]))

    @action(
        description=_("Accept"),
        url_path="approve",
        icon="check_circle",
        permissions=["review_product"],
    )
    def approve_detail(self, request, object_id):
        return self._run(request, object_id, catalog.approve)

    @action(
        description=_("Refuse and block"),
        url_path="refuse",
        icon="block",
        permissions=["review_product"],
    )
    def refuse_detail(self, request, object_id):
        product = get_object_or_404(Product, pk=object_id)
        form = RefuseForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            return self._run(request, object_id, catalog.refuse, reason=form.cleaned_data["reason"])
        context = {
            **self.admin_site.each_context(request),
            "title": _("Refuse « %(title)s »") % {"title": product.title},
            "opts": self.model._meta,
            "form": form,
            "product": product,
        }
        return TemplateResponse(request, "admin/shop/refuse_product.html", context)

    @action(
        description=_("Unblock (back to draft)"),
        url_path="unblock",
        icon="lock_open",
        permissions=["review_product"],
    )
    def unblock_detail(self, request, object_id):
        return self._run(request, object_id, catalog.unblock)


class ZoneInline(TabularInline):
    model = DeliveryZone
    fields = ["mode", "name", "fee_minor", "is_active"]
    extra = 0
    tab = True


@admin.register(ShopProfile)
class ShopProfileAdmin(AuditedModelAdmin):
    list_display = ["pro", "is_open", "pickup", "seller_delivery", "partner_delivery"]
    list_filter = ["is_open", "pickup", "seller_delivery", "partner_delivery"]
    search_fields = ["pro__business_name", "pro__slug"]
    readonly_fields = ["pro"]
    inlines = [ZoneInline]

    def has_add_permission(self, request):
        return False


class OrderLineInline(TabularInline):
    model = OrderLine
    fields = ["title", "variant_label", "unit_price_minor", "quantity", "total_minor"]
    readonly_fields = fields
    extra = 0
    tab = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(AuditedModelAdmin):
    """Read only: what happens to the money is decided in Finance (payments, disputes)."""

    list_display = ["reference", "pro", "buyer", "status", "total", "delivery_mode", "created_at"]
    list_filter = ["status", "delivery_mode", "currency"]
    search_fields = ["reference", "pro__business_name", "buyer__first_name"]
    date_hierarchy = "created_at"
    inlines = [OrderLineInline]
    exclude = ["contact_phone"]  # personal: seen by the seller only

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields if f.name != "contact_phone"] + [
            "payment_link"
        ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @display(description=_("total"))
    def total(self, order):
        return amount(order.items_minor + order.delivery_minor, order.currency)

    @display(description=_("payment"))
    def payment_link(self, order):
        url = reverse("admin:payments_payment_change", args=[order.payment_id])
        return format_html('<a href="{}">{}</a>', url, order.payment.reference)


@admin.register(PromoCode)
class PromoCodeAdmin(AuditedModelAdmin):
    list_display = ["code", "pro", "percent_off", "amount_off_minor", "ends_at", "is_active"]
    list_filter = ["is_active", "currency"]
    search_fields = ["code", "pro__business_name"]
    readonly_fields = ["pro", "currency"]

    def has_add_permission(self, request):
        return False


@admin.register(FlashSale)
class FlashSaleAdmin(AuditedModelAdmin):
    list_display = [
        "product",
        "percent_off",
        "starts_at",
        "ends_at",
        "quantity_limit",
        "sold_count",
    ]
    search_fields = ["product__title"]
    readonly_fields = ["product", "sold_count"]

    def has_add_permission(self, request):
        return False


class BundleItemInline(TabularInline):
    model = BundleItem
    fields = ["variant", "quantity"]
    readonly_fields = fields
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Bundle)
class BundleAdmin(AuditedModelAdmin):
    list_display = ["title", "pro", "price_minor", "currency", "is_active"]
    list_filter = ["is_active", "currency"]
    search_fields = ["title", "pro__business_name"]
    readonly_fields = ["pro", "currency"]
    exclude = ["photo"]
    inlines = [BundleItemInline]

    def has_add_permission(self, request):
        return False


class LivePinInline(TabularInline):
    model = LivePin
    fields = ["product", "pinned_at", "unpinned_at"]
    readonly_fields = fields
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SaleLive)
class SaleLiveAdmin(AuditedModelAdmin):
    """Sales lives of the shops: when, orders and sales made on air. Cutting a live and
    deleting a replay happen in « Live rooms »."""

    list_display = ["title", "pro", "starts_at", "status", "orders_count", "revenue_minor"]
    list_filter = ["status", "currency"]
    search_fields = ["title", "pro__business_name"]
    date_hierarchy = "starts_at"
    readonly_fields = [
        "pro",
        "title",
        "description",
        "starts_at",
        "duration_minutes",
        "status",
        "orders_count",
        "revenue_minor",
        "currency",
    ]
    fields = readonly_fields
    inlines = [LivePinInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
