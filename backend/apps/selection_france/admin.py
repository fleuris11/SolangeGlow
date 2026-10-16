"""France Selection in the back office: catalogue with the price calculation, the queue of
orders to place at the merchants, shipments, special requests and group pre-orders."""

from __future__ import annotations

from django import forms
from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TabbedTranslationAdmin
from unfold.admin import TabularInline
from unfold.decorators import action, display

from apps.core.audit.admin import AuditedModelAdmin
from apps.core.errors import DomainError
from apps.core.media.services import create_asset, variant_url
from apps.core.money import Money

from . import pricing, selectors, services
from .models import (
    GroupBuy,
    PickupPoint,
    SelectionCategory,
    SelectionOrder,
    SelectionPhoto,
    SelectionProduct,
    Shipment,
    SpecialRequest,
)


def xof(amount) -> str:
    return Money(int(amount or 0), "XOF").format("fr") if amount is not None else "—"


def euros(value) -> str:
    return f"{value:.2f} €".replace(".", ",")


def breakdown_table(rows: list[tuple[str, str]]):
    return format_html(
        '<table class="text-sm">{}</table>',
        format_html_join(
            "",
            '<tr><td class="pr-4 py-1">{}</td><td class="text-right font-semibold">{}</td></tr>',
            rows,
        ),
    )


def breakdown_rows(b: pricing.Breakdown) -> list[tuple[str, str]]:
    return [
        (_("Purchase price"), euros(b.purchase)),
        (_("+ transport (weight x price per kg)"), euros(b.transport)),
        (_("+ packaging"), euros(b.packaging)),
        (_("= subtotal"), euros(b.subtotal)),
        (_("x (1 + customs)"), euros(b.with_customs)),
        (_("x (1 + margin)"), euros(b.with_margin)),
        (_("+ payment fees"), euros(b.payment_fee)),
        (_("= total in euros"), euros(b.total_eur)),
        (_("x rate"), str(b.rate)),
        (_("= exact FCFA"), f"{b.exact_xof:.0f}"),
        (_("Price (rounded up)"), xof(b.price_xof)),
    ]


def _run(modeladmin, request, step, done) -> bool:
    try:
        step()
    except DomainError as exc:
        modeladmin.message_user(request, exc.text(), messages.ERROR)
        return False
    modeladmin.message_user(request, done, messages.SUCCESS)
    return True


def _form_page(modeladmin, request, *, title, form, help_text, back):
    context = {
        **modeladmin.admin_site.each_context(request),
        "title": title,
        "opts": modeladmin.model._meta,
        "form": form,
        "help": help_text,
        "back": back,
    }
    return TemplateResponse(request, "admin/selection_france/form.html", context)


# --- Catalogue -----------------------------------------------------------------------------------


@admin.register(SelectionCategory)
class SelectionCategoryAdmin(AuditedModelAdmin, TabbedTranslationAdmin):
    list_display = ["name", "key", "air_restricted", "margin_bps", "customs_bps", "is_active"]
    list_filter = ["air_restricted", "is_active"]
    actions = ["reprice_products"]

    @admin.action(description=_("Recalculate the prices of their products"))
    def reprice_products(self, request, queryset):
        count = services.reprice_all(SelectionProduct.objects.filter(category__in=queryset))
        self.message_user(request, _("%(count)s prices recalculated.") % {"count": count})


class PhotoForm(forms.ModelForm):
    upload = forms.ImageField(label=_("picture"), required=False)

    class Meta:
        model = SelectionPhoto
        fields = ["position"]


class PhotoInline(TabularInline):
    model = SelectionPhoto
    form = PhotoForm
    fields = ["preview", "upload", "position"]
    readonly_fields = ["preview"]
    extra = 1
    tab = True

    @display(description=_("photo"))
    def preview(self, photo):
        url = variant_url(photo.media, "thumb") if photo.pk and photo.media_id else None
        return format_html('<img src="{}" width="80" height="80" alt="">', url) if url else "—"


@admin.register(SelectionProduct)
class SelectionProductAdmin(AuditedModelAdmin):
    list_display = [
        "title",
        "merchant_name",
        "aisle",
        "category",
        "price",
        "express",
        "availability",
        "sold_count",
    ]
    list_filter = ["aisle", "category", "availability"]
    search_fields = ["title", "merchant_name"]
    prepopulated_fields = {"slug": ["title"]}
    readonly_fields = ["calculation", "priced_at", "sold_count"]
    fields = [
        "title",
        "slug",
        "aisle",
        "category",
        "availability",
        "merchant_name",
        "merchant_url",
        "purchase_price_cents",
        "weight_grams",
        "options",
        "description",
        "calculation",
        "priced_at",
        "sold_count",
    ]
    inlines = [PhotoInline]
    actions = ["reprice"]

    @display(description=_("price"), ordering="price_xof")
    def price(self, product):
        return xof(product.price_xof)

    @display(description=_("express"))
    def express(self, product):
        return xof(product.express_price_xof)

    @display(description=_("price calculation"))
    def calculation(self, product):
        if not product.pk:
            return _("Saved first, then calculated.")
        grouped = pricing.price_of(product)
        parts = [format_html("<p><strong>{}</strong></p>", _("Weekly grouped shipment"))]
        parts.append(breakdown_table(breakdown_rows(grouped)))
        if pricing.express_allowed(product.category):
            express = pricing.price_of(product, express=True)
            parts.append(format_html("<p class='mt-4'><strong>{}</strong></p>", _("Express")))
            parts.append(breakdown_table(breakdown_rows(express)))
        else:
            parts.append(format_html("<p class='mt-4'>{}</p>", _("No express: forbidden by air.")))
        return format_html("{}" * len(parts), *parts)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        services.reprice(obj)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for photo_form in formset.forms:
            upload = photo_form.cleaned_data.get("upload") if photo_form.cleaned_data else None
            if upload:
                photo = photo_form.instance
                photo.product = form.instance
                photo.media = create_asset(
                    owner=request.user, uploaded=upload, purpose="selection_photo"
                )
                photo.save()
        for instance in instances:
            if instance.media_id:
                instance.save()
        for deleted in formset.deleted_objects:
            deleted.delete()

    @admin.action(description=_("Recalculate the prices"))
    def reprice(self, request, queryset):
        count = services.reprice_all(queryset)
        self.message_user(request, _("%(count)s prices recalculated.") % {"count": count})


@admin.register(PickupPoint)
class PickupPointAdmin(AuditedModelAdmin):
    list_display = ["name", "city", "address", "hours", "is_active"]
    list_editable = ["is_active"]


# --- Orders and shipments ------------------------------------------------------------------------


class MerchantOrderForm(forms.Form):
    merchant_order_number = forms.CharField(label=_("Merchant order number"), max_length=80)


class CodeForm(forms.Form):
    code = forms.CharField(label=_("Receipt code of the client"), min_length=6, max_length=6)


@admin.register(SelectionOrder)
class SelectionOrderAdmin(AuditedModelAdmin):
    list_display = [
        "reference",
        "title",
        "option",
        "quantity",
        "merchant",
        "shipping_mode",
        "status",
        "pickup_point",
        "created_at",
    ]
    list_filter = ["status", "shipping_mode", "pickup_point"]
    search_fields = ["reference", "title", "merchant_order_number", "buyer__first_name"]
    actions = ["to_shipment"]
    actions_detail = ["ordered_detail", "received_detail", "code_detail"]

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields] + ["merchant"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @display(description=_("merchant"))
    def merchant(self, order):
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">{} ({})</a>',
            order.merchant_url,
            order.merchant_name or _("link"),
            euros(order.purchase_price_cents / 100),
        )

    def _back(self, object_id):
        return redirect(reverse("admin:selection_france_selectionorder_change", args=[object_id]))

    @action(description=_("Ordered at the merchant"), url_path="ordered", icon="shopping_cart")
    def ordered_detail(self, request, object_id):
        order = get_object_or_404(SelectionOrder, pk=object_id)
        form = MerchantOrderForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            _run(
                self,
                request,
                lambda: services.mark_ordered(
                    order,
                    actor=request.user,
                    merchant_order_number=form.cleaned_data["merchant_order_number"],
                ),
                _("Marked as ordered; the client is told."),
            )
            return self._back(object_id)
        return _form_page(
            self,
            request,
            title=_("Order placed: %(reference)s") % {"reference": order.reference},
            form=form,
            help_text=format_html(
                '{} <a class="underline" href="{}" target="_blank" rel="noopener">{}</a>',
                _("Buy it at the merchant, then give the order number."),
                order.merchant_url,
                order.merchant_name or order.merchant_url,
            ),
            back=reverse("admin:selection_france_selectionorder_change", args=[object_id]),
        )

    @action(description=_("Received in France"), url_path="received", icon="inventory")
    def received_detail(self, request, object_id):
        order = get_object_or_404(SelectionOrder, pk=object_id)
        _run(
            self,
            request,
            lambda: services.mark_received(order, actor=request.user),
            _("Received; it can go in the next shipment."),
        )
        return self._back(object_id)

    @action(description=_("Type the receipt code"), url_path="code", icon="key")
    def code_detail(self, request, object_id):
        order = get_object_or_404(SelectionOrder, pk=object_id)
        form = CodeForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            _run(
                self,
                request,
                lambda: services.hand_over(order, form.cleaned_data["code"], actor=request.user),
                _("Handed over: the money is released."),
            )
            return self._back(object_id)
        return _form_page(
            self,
            request,
            title=_("Hand over %(reference)s") % {"reference": order.reference},
            form=form,
            help_text=_("The client gives her 6-digit code when she takes her parcel."),
            back=reverse("admin:selection_france_selectionorder_change", args=[object_id]),
        )

    @admin.action(description=_("Put in a new shipment"))
    def to_shipment(self, request, queryset):
        holder = {}

        def create():
            holder["shipment"] = services.new_shipment(list(queryset), actor=request.user)

        if _run(self, request, create, _("Shipment created: add the carrier and tracking.")):
            return redirect(
                reverse("admin:selection_france_shipment_change", args=[holder["shipment"].pk])
            )
        return None


class ShipmentOrderInline(TabularInline):
    model = SelectionOrder
    fields = ["reference", "title", "quantity", "status", "pickup_point"]
    readonly_fields = fields
    extra = 0
    can_delete = False
    tab = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Shipment)
class ShipmentAdmin(AuditedModelAdmin):
    list_display = ["reference", "mode", "carrier", "tracking_number", "status", "departed_at"]
    list_filter = ["status", "mode"]
    search_fields = ["reference", "tracking_number"]
    readonly_fields = ["reference", "mode", "status", "departed_at", "arrived_at"]
    fields = [
        "reference",
        "mode",
        "carrier",
        "tracking_number",
        "note",
        "status",
        "departed_at",
        "arrived_at",
    ]
    inlines = [ShipmentOrderInline]
    actions_detail = ["depart_detail", "arrive_detail"]

    def has_add_permission(self, request):
        return False  # made from the orders received in France

    def _back(self, object_id):
        return redirect(reverse("admin:selection_france_shipment_change", args=[object_id]))

    @action(description=_("Shipment left"), url_path="depart", icon="flight_takeoff")
    def depart_detail(self, request, object_id):
        shipment = get_object_or_404(Shipment, pk=object_id)
        _run(
            self,
            request,
            lambda: services.depart(shipment, actor=request.user),
            _("On its way: the clients see the tracking."),
        )
        return self._back(object_id)

    @action(description=_("Shipment arrived"), url_path="arrive", icon="flight_land")
    def arrive_detail(self, request, object_id):
        shipment = get_object_or_404(Shipment, pk=object_id)
        _run(
            self,
            request,
            lambda: services.arrive(shipment, actor=request.user),
            _("Arrived: the clients are told to come with their code."),
        )
        return self._back(object_id)


# --- Special requests and group pre-orders --------------------------------------------------------


class RefuseForm(forms.Form):
    answer = forms.CharField(label=_("Why (shown to the client)"), max_length=500)


@admin.register(SpecialRequest)
class SpecialRequestAdmin(AuditedModelAdmin):
    list_display = ["__str__", "client", "status", "price_xof", "valid_until", "created_at"]
    list_filter = ["status"]
    search_fields = ["title", "link", "client__first_name"]
    readonly_fields = ["client", "request_link", "request_photo", "note", "status", "quote"]
    fields = [
        "client",
        "request_link",
        "request_photo",
        "note",
        "status",
        "title",
        "merchant_name",
        "merchant_url",
        "purchase_price_cents",
        "weight_grams",
        "category",
        "quote",
        "price_xof",
        "answer",
    ]
    actions_detail = ["quote_detail", "refuse_detail"]

    def has_add_permission(self, request):
        return False

    @display(description=_("link"))
    def request_link(self, request_obj):
        if not request_obj.link:
            return "—"
        return format_html(
            '<a class="underline" href="{}" target="_blank" rel="noopener">{}</a>',
            request_obj.link,
            request_obj.link[:80],
        )

    @display(description=_("photo"))
    def request_photo(self, request_obj):
        url = variant_url(request_obj.photo, "medium") if request_obj.photo_id else None
        return format_html('<img src="{}" width="240" alt="">', url) if url else "—"

    @display(description=_("price calculation"))
    def quote(self, request_obj):
        grouped = services.quote_breakdown(request_obj)
        if grouped is None:
            return _("Fill the purchase price, the weight and the category, then save.")
        return breakdown_table(breakdown_rows(grouped))

    def _back(self, object_id):
        return redirect(reverse("admin:selection_france_specialrequest_change", args=[object_id]))

    @action(description=_("Send the quote"), url_path="quote", icon="send")
    def quote_detail(self, request, object_id):
        found = get_object_or_404(SpecialRequest, pk=object_id)
        _run(
            self,
            request,
            lambda: services.send_quote(found, actor=request.user),
            _("Quote sent to the client."),
        )
        return self._back(object_id)

    @action(description=_("Not possible"), url_path="refuse", icon="block")
    def refuse_detail(self, request, object_id):
        found = get_object_or_404(SpecialRequest, pk=object_id)
        form = RefuseForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            _run(
                self,
                request,
                lambda: services.refuse_request(
                    found, actor=request.user, answer=form.cleaned_data["answer"]
                ),
                _("The client is told."),
            )
            return self._back(object_id)
        return _form_page(
            self,
            request,
            title=_("Request not possible"),
            form=form,
            help_text=_("Say why in a few simple words."),
            back=reverse("admin:selection_france_specialrequest_change", args=[object_id]),
        )


@admin.register(GroupBuy)
class GroupBuyAdmin(AuditedModelAdmin):
    list_display = ["product", "progress", "price", "ends_at", "status"]
    list_filter = ["status"]
    readonly_fields = ["status", "closed_at", "progress", "normal_price"]
    fields = [
        "product",
        "normal_price",
        "price_xof",
        "target_quantity",
        "ends_at",
        "progress",
        "status",
        "closed_at",
    ]
    autocomplete_fields = []

    @display(description=_("orders"))
    def progress(self, group):
        if not group.pk:
            return "—"
        return f"{selectors.group_count(group)} / {group.target_quantity}"

    @display(description=_("group price"))
    def price(self, group):
        return xof(group.price_xof)

    @display(description=_("normal price"))
    def normal_price(self, group):
        return xof(group.product.price_xof) if group.pk else "—"
