"""Prospects, corrected translations and the sign-ins as a member in the back office."""

from __future__ import annotations

from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TabbedTranslationAdmin
from unfold.admin import TabularInline
from unfold.decorators import action, display

from apps.core.audit.admin import AuditedModelAdmin
from apps.core.errors import DomainError
from apps.pros.errors import NotReadyToPublish

from .models import (
    Impersonation,
    Prospect,
    ProspectEmailTemplate,
    ProspectMessage,
    TranslationOverride,
)
from .services import prospects, translations


class MessageInline(TabularInline):
    """The e-mails already sent to this prospect (read only)."""

    model = ProspectMessage
    fields = ["created_at", "subject", "status", "sent_by"]
    readonly_fields = fields
    extra = 0
    tab = True
    verbose_name_plural = _("e-mails sent")

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# What « Publish » still needs, in words (codes of pros.services.missing_for_publication).
MISSING = {
    "business_name": _("their name"),
    "slug": _("the address of the page"),
    "trades": _("their trade"),
    "city": _("their city"),
    "location": _("their place on the map"),
    "services": _("at least one service"),
    "where": _("where they receive clients"),
}

STATUS_COLORS = {
    Prospect.Status.NEW: "info",
    Prospect.Status.CONTACTED: "warning",
    Prospect.Status.SIGNED_UP: "success",
    Prospect.Status.ACTIVE: "success",
    Prospect.Status.DECLINED: "danger",
}


@admin.register(Prospect)
class ProspectAdmin(AuditedModelAdmin):
    """Prospecting from one screen: who they are, their prepared showcase, the messages sent.

    1. « Prepare the showcase »: an account without password, their name, trade, address,
       WhatsApp and page, online booking off.
    2. « Complete the showcase »: sign in as them to add the photos of their work, a service
       and their place on the map.
    3. « Publish the showcase »: online, with the band « prepared by Solange Glow », their
       WhatsApp and « remove my page ».
    4. « Write on WhatsApp » or « Send an e-mail »: a message in their name with their personal
       link. They choose their password and the page is theirs."""

    list_display = [
        "name",
        "business_name",
        "country",
        "city",
        "trade",
        "status_label",
        "showcase_state",
        "last_message_at",
        "owner",
    ]
    list_filter = ["status", "country", "language", "trade", "source", "owner"]
    search_fields = ["name", "business_name", "phone", "email", "notes", "city"]
    readonly_fields = [
        "invite_link",
        "invited_at",
        "last_message_at",
        "signed_up_user",
        "showcase_state",
    ]
    fieldsets = (
        (
            _("Who they are"),
            {
                "fields": (
                    "name",
                    "business_name",
                    "trade",
                    "address",
                    "city",
                    "country",
                    "language",
                )
            },
        ),
        (_("How to reach them"), {"fields": ("email", "phone", "website")}),
        (_("What they do, what we offer"), {"fields": ("services", "pitch", "notes")}),
        (
            _("Follow-up"),
            {"fields": ("status", "owner", "source", "invited_at", "last_message_at")},
        ),
        (
            _("Showcase and account"),
            {"fields": ("showcase_state", "invite_link", "signed_up_user")},
        ),
    )
    inlines = [MessageInline]
    actions = ["email_presentation", "prepare_showcases", "publish_showcases", "send_invitation"]
    actions_list = ["import_list", "open_templates"]
    actions_detail = [
        "prepare_showcase_detail",
        "open_showcase_detail",
        "publish_showcase_detail",
        "whatsapp_detail",
        "share_detail",
        "email_detail",
    ]

    def get_changeform_initial_data(self, request):
        return {**super().get_changeform_initial_data(request), "owner": request.user.pk}

    def save_model(self, request, obj, form, change):
        if not change and "language" not in form.changed_data:
            obj.language = prospects.default_language(obj.country)
        obj.country = (obj.country or "").upper()
        super().save_model(request, obj, form, change)

    @display(description=_("status"), label=STATUS_COLORS)
    def status_label(self, prospect):
        return prospect.status, prospect.get_status_display()

    @display(description=_("showcase"))
    def showcase_state(self, prospect):
        if not prospect.pk or not prospect.pro_id:
            return _("Not prepared")
        link = prospects.showcase_link(prospect)
        state = f"{prospect.pro.business_name} · {prospect.pro.get_status_display()}"
        if not link:
            return state
        return format_html(
            '{} · <a href="{}" target="_blank" rel="noopener">{}</a>', state, link, link
        )

    @display(description=_("sign-up link"))
    def invite_link(self, prospect):
        return prospects.link_of(prospect) if prospect.pk else "—"

    def _back(self, object_id):
        return redirect(reverse("admin:backoffice_prospect_change", args=[object_id]))

    @action(description=_("Prepare her showcase"), url_path="prepare", icon="storefront")
    def prepare_showcase_detail(self, request, object_id):
        prospect = self.get_object(request, object_id)
        pro = prospects.prepare_showcase(prospect, actor=request.user)
        self.message_user(
            request,
            _("Draft showcase « %(name)s » ready. Complete it, then send the e-mail.")
            % {"name": pro.business_name},
            messages.SUCCESS,
        )
        return self._back(object_id)

    @action(description=_("Complete her showcase (as her)"), url_path="showcase", icon="edit")
    def open_showcase_detail(self, request, object_id):
        prospect = self.get_object(request, object_id)
        if not prospect.pro_id:
            self.message_user(request, _("Prepare her showcase first."), messages.WARNING)
            return self._back(object_id)
        return redirect(reverse("admin:backoffice_impersonate", args=[prospect.pro.user_id]))

    @action(description=_("Publish the showcase"), url_path="publish", icon="public")
    def publish_showcase_detail(self, request, object_id):
        prospect = self.get_object(request, object_id)
        try:
            prospects.publish_showcase(prospect, actor=request.user)
        except NotReadyToPublish as error:
            missing = [str(MISSING.get(code, code)) for code in error.details.get("missing", [])]
            self.message_user(
                request,
                _("Still missing before publishing: %(missing)s. Use « Complete the showcase ».")
                % {"missing": ", ".join(missing)},
                messages.WARNING,
            )
            return self._back(object_id)
        self.message_user(
            request,
            _("Showcase online: %(link)s. Write to them now, on WhatsApp or by e-mail.")
            % {"link": prospects.showcase_link(prospect)},
            messages.SUCCESS,
        )
        return self._back(object_id)

    @action(description=_("Write on WhatsApp"), url_path="whatsapp", icon="chat")
    def whatsapp_detail(self, request, object_id):
        prospect = self.get_object(request, object_id)
        url = prospects.whatsapp_to_prospect(prospect)
        if prospect.status == Prospect.Status.DECLINED:
            self.message_user(
                request, _("They asked not to be contacted any more."), messages.ERROR
            )
            return self._back(object_id)
        if not url:
            self.message_user(
                request, _("Add their phone number, with the country code."), messages.WARNING
            )
            return self._back(object_id)
        prospects.mark_written(prospect, actor=request.user, channel="whatsapp")
        return redirect(url)

    @action(description=_("Share on WhatsApp"), url_path="share", icon="share")
    def share_detail(self, request, object_id):
        prospect = self.get_object(request, object_id)
        url = prospects.whatsapp_share(prospect)
        if not url:
            self.message_user(request, _("Publish the showcase first."), messages.WARNING)
            return self._back(object_id)
        return redirect(url)

    @action(description=_("Send an e-mail"), url_path="email", icon="mail")
    def email_detail(self, request, object_id):
        return redirect(reverse("admin:backoffice_prospect_email", args=[object_id]))

    @admin.action(description=_("Send the presentation e-mail"))
    def email_presentation(self, request, queryset):
        template = ProspectEmailTemplate.objects.filter(key="presentation", is_active=True).first()
        if template is None:
            self.message_user(
                request, _("The standard e-mail « presentation » is missing."), messages.ERROR
            )
            return
        sent = skipped = 0
        for prospect in queryset:
            try:
                prospects.send_email(prospect, template, actor=request.user)
                sent += 1
            except DomainError as error:
                skipped += 1
                if error.code == "daily_email_limit":
                    self.message_user(request, error.text(), messages.WARNING)
                    break
        self.message_user(
            request,
            _("%(sent)s e-mails leaving, %(skipped)s skipped (no address, or asked to stop).")
            % {"sent": sent, "skipped": skipped},
            messages.SUCCESS,
        )

    @admin.action(description=_("Publish the prepared showcases"))
    def publish_showcases(self, request, queryset):
        done = skipped = 0
        for prospect in queryset.filter(pro__isnull=False):
            try:
                prospects.publish_showcase(prospect, actor=request.user)
                done += 1
            except DomainError:
                skipped += 1
        self.message_user(
            request,
            _("%(done)s showcases online, %(skipped)s not complete yet (open them one by one).")
            % {"done": done, "skipped": skipped},
            messages.SUCCESS,
        )

    @admin.action(description=_("Prepare the showcases"))
    def prepare_showcases(self, request, queryset):
        done = skipped = 0
        for prospect in queryset.filter(pro__isnull=True):
            try:
                prospects.prepare_showcase(prospect, actor=request.user)
                done += 1
            except DomainError:
                skipped += 1
        self.message_user(
            request,
            _("%(done)s showcases prepared, %(skipped)s skipped (no e-mail, or account exists).")
            % {"done": done, "skipped": skipped},
            messages.SUCCESS,
        )

    @admin.action(description=_("Send the invitation (WhatsApp, else SMS)"))
    def send_invitation(self, request, queryset):
        sent = sum(prospects.invite(p, actor=request.user) for p in queryset)
        self.message_user(
            request,
            _("%(count)s invitations sent (a prospect without a phone is skipped).")
            % {"count": sent},
            messages.SUCCESS,
        )

    @action(description=_("Import a CSV file"), url_path="import", icon="upload_file")
    def import_list(self, request):
        return redirect(reverse("admin:backoffice_prospects_import"))

    @action(description=_("Standard e-mails"), url_path="templates", icon="drafts")
    def open_templates(self, request):
        return redirect(reverse("admin:backoffice_prospectemailtemplate_changelist"))


@admin.register(ProspectEmailTemplate)
class ProspectEmailTemplateAdmin(AuditedModelAdmin, TabbedTranslationAdmin):
    """The standard e-mails. Words between braces are replaced for each prospect:
    {{ name }}, {{ business }}, {{ activity }}, {{ city }}, {{ pitch }}, {{ showcase_link }},
    {{ link }}, {{ stop_link }}."""

    list_display = ["name", "key", "needs_showcase", "position", "is_active"]
    list_editable = ["position", "is_active"]
    search_fields = ["name", "key", "subject", "body"]
    fieldsets = (
        (None, {"fields": ("name", "key", "needs_showcase", "position", "is_active")}),
        (
            _("Text"),
            {
                "fields": ("subject", "body"),
                "description": _(
                    "Replaced for each prospect: {{ name }} (first name), {{ business }}, "
                    "{{ activity }} (trade and city), {{ city }}, {{ pitch }} (our proposal), "
                    "{{ showcase_link }} (their showcase online), {{ link }} (their personal "
                    "link) and {{ stop_link }} (« not interested », to keep at the bottom)."
                ),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        return ["key"] if obj else []


@admin.register(ProspectMessage)
class ProspectMessageAdmin(AuditedModelAdmin):
    """The journal of the e-mails sent to the prospects (read only)."""

    list_display = ["created_at", "prospect", "subject", "status", "sent_by"]
    list_filter = ["status", "template_key", "sent_by"]
    search_fields = ["to_email", "subject", "prospect__name", "prospect__business_name"]
    readonly_fields = [f.name for f in ProspectMessage._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(TranslationOverride)
class TranslationOverrideAdmin(AuditedModelAdmin):
    list_display = ["key", "language", "domain", "text", "updated_by", "updated_at"]
    list_filter = ["domain", "language"]
    search_fields = ["key", "text"]
    readonly_fields = ["updated_by"]
    actions_list = ["open_search"]

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        translations.changed()

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        translations.changed()

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        translations.changed()

    @action(description=_("Search a text"), url_path="search", icon="search")
    def open_search(self, request):
        return redirect(reverse("admin:backoffice_translations"))


@admin.register(Impersonation)
class ImpersonationAdmin(AuditedModelAdmin):
    list_display = ["created_at", "staff", "target", "reason", "expires_at", "ended_at", "actions"]
    list_filter = ["staff"]
    search_fields = ["target__email", "target__phone", "staff__email", "reason"]
    readonly_fields = [f.name for f in Impersonation._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
