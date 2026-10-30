"""Pages of the back office that are not plain lists (ADR-001): two-factor sign-in, the
team, the switches, the translations, the consoles, « sign in as » a member."""

from __future__ import annotations

from urllib.parse import quote

import segno
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme, urlencode
from django.utils.translation import gettext_lazy as _

from apps.accounts.cookies import set_auth_cookies
from apps.core.audit.services import record
from apps.core.errors import DomainError
from apps.core.models import Country, FeatureFlag

from .models import Prospect, StaffDevice, TranslationOverride
from .services import impersonation, prospects, team, translations, twofactor


def _require(request, perm: str | None) -> None:
    user = request.user
    if not (user.is_superuser or (perm and user.has_perm(f"backoffice.{perm}"))):
        raise PermissionDenied


def _page(site, request, template: str, title, **context):
    return TemplateResponse(
        request,
        f"admin/backoffice/{template}",
        {**site.each_context(request), "title": title, **context},
    )


# --- Two-factor sign-in ------------------------------------------------------------------------


def two_factor_view(site):
    def view(request):
        user = request.user
        target = request.GET.get("next") or reverse("admin:index")
        if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
            target = reverse("admin:index")
        set_up = twofactor.is_set_up(user)
        error = ""
        if request.method == "POST":
            code = request.POST.get("code", "")
            backup = request.POST.get("backup", "")
            ok = (
                twofactor.use_recovery_code(user, backup)
                if backup and set_up
                else twofactor.verify(user, code)
            )
            if ok:
                twofactor.mark_verified(request)
                record("backoffice.two_factor_passed", user, actor=user)
                if not set_up:
                    codes = twofactor.new_recovery_codes(user)
                    return _page(
                        site,
                        request,
                        "recovery_codes.html",
                        _("Your backup codes"),
                        codes=codes,
                        target=target,
                    )
                return HttpResponseRedirect(target)
            error = _("The code does not match. Check the 6 digits of your app and try again.")
        context = {"set_up": set_up, "error": error, "target": target}
        if not set_up:
            device = twofactor.device_of(user)
            secret = twofactor.secret_of(device)
            uri = twofactor.provisioning_uri(secret, user.email or str(user.phone))
            context.update(
                secret=secret,
                qr=segno.make(uri, error="m").svg_inline(scale=5, dark="#3B1233"),
            )
        return _page(site, request, "two_factor.html", _("Two-factor sign-in"), **context)

    return view


# --- Team --------------------------------------------------------------------------------------


class MemberForm(forms.Form):
    email = forms.EmailField(label=_("E-mail"))
    first_name = forms.CharField(label=_("First name"), max_length=150)
    password = forms.CharField(
        label=_("Temporary password"),
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text=_("Empty: unchanged. She sets up two-factor at her first sign-in."),
    )
    roles = forms.MultipleChoiceField(
        label=_("Roles"),
        required=False,
        choices=[(key, label) for key, (_name, label, _perms) in team.ROLES.items()],
        widget=forms.CheckboxSelectMultiple,
    )


def team_view(site):
    def view(request):
        _require(request, "manage_team")
        User = get_user_model()
        form = MemberForm(request.POST or None)
        if request.method == "POST":
            action = request.POST.get("action", "save")
            if action in ("reset", "remove"):
                member = get_object_or_404(User, pk=request.POST.get("user"), is_staff=True)
                if member.is_superuser and not request.user.is_superuser:
                    raise PermissionDenied
                if action == "reset":
                    twofactor.reset(member, actor=request.user)
                    messages.success(request, _("Two-factor reset: she sets it up again."))
                else:
                    team.remove_member(member, actor=request.user)
                    messages.success(request, _("She is no longer in the team."))
                return redirect(reverse("admin:backoffice_team"))
            if form.is_valid():
                team.save_member(actor=request.user, **form.cleaned_data)
                messages.success(request, _("Team member saved."))
                return redirect(reverse("admin:backoffice_team"))
        devices = set(
            StaffDevice.objects.filter(confirmed_at__isnull=False).values_list("user_id", flat=True)
        )
        members = [
            {
                "user": member,
                "roles": [str(team.ROLES[key][1]) for key in team.roles_of(member)],
                "two_factor": member.pk in devices,
            }
            for member in User.objects.filter(is_staff=True)
            .prefetch_related("groups")
            .order_by("first_name")
        ]
        return _page(site, request, "team.html", _("Team"), form=form, members=members)

    return view


# --- Switches ----------------------------------------------------------------------------------


def flags_view(site):
    def view(request):
        _require(request, "manage_flags")
        countries = list(Country.objects.filter(is_active=True))
        if request.method == "POST":
            flag = get_object_or_404(FeatureFlag, pk=request.POST.get("flag"))
            what = request.POST.get("what", "")
            before = {
                "enabled": flag.is_enabled,
                "countries": sorted(flag.countries.values_list("code", flat=True)),
                "roles": list(flag.roles),
            }
            if what == "enabled":
                flag.is_enabled = not flag.is_enabled
                flag.save()
            elif what.startswith("country:"):
                country = get_object_or_404(Country, code=what.split(":", 1)[1])
                if flag.countries.filter(pk=country.pk).exists():
                    flag.countries.remove(country)
                else:
                    flag.countries.add(country)
            elif what.startswith("role:"):
                role = what.split(":", 1)[1]
                roles = set(flag.roles)
                roles.symmetric_difference_update({role})
                flag.roles = sorted(roles)
                flag.save()
            record(
                "backoffice.flag_changed",
                flag,
                actor=request.user,
                before=before,
                after={
                    "enabled": flag.is_enabled,
                    "countries": sorted(flag.countries.values_list("code", flat=True)),
                    "roles": list(flag.roles),
                },
            )
            return redirect(reverse("admin:backoffice_flags"))
        from apps.core.choices import Role

        rows = [
            {
                "flag": flag,
                "countries": [
                    (c.code, c.code in {x.code for x in flag.countries.all()}) for c in countries
                ],
                "roles": [(value, label, value in flag.roles) for value, label in Role.choices],
            }
            for flag in FeatureFlag.objects.prefetch_related("countries")
        ]
        return _page(
            site,
            request,
            "flags.html",
            _("Features by country and role"),
            rows=rows,
            countries=countries,
        )

    return view


# --- Translations ------------------------------------------------------------------------------


def translations_view(site):
    def view(request):
        _require(request, "edit_translations")
        language = request.GET.get("lang") or request.POST.get("lang") or "fr"
        if language not in dict(settings.LANGUAGES):
            language = "fr"
        query = request.GET.get("q", "")
        if request.method == "POST":
            domain = request.POST.get("domain")
            if domain in TranslationOverride.Domain.values:
                translations.save(
                    domain=domain,
                    language=language,
                    key=request.POST.get("key", ""),
                    text=request.POST.get("text", ""),
                    actor=request.user,
                )
                messages.success(request, _("Saved: the app uses it within a minute."))
            query = urlencode({"lang": language, "q": request.POST.get("q", "")})
            return redirect(f"{reverse('admin:backoffice_translations')}?{query}")
        return _page(
            site,
            request,
            "translations.html",
            _("Texts of the interface"),
            rows=translations.search(query, language),
            query=query,
            language=language,
            languages=settings.LANGUAGES,
            count=TranslationOverride.objects.count(),
        )

    return view


# --- Consoles ----------------------------------------------------------------------------------


def moderation_console(site):
    def view(request):
        _require(request, "use_moderation_console")
        from apps.moderation.models import ModerationCase

        cases = (
            ModerationCase.objects.filter(status=ModerationCase.Status.PENDING)
            .select_related("author", "target_type")
            .order_by("-hidden_until_review", "-report_count", "created_at")[:100]
        )
        return _page(site, request, "moderation.html", _("Moderation console"), cases=cases)

    return view


def disputes_console(site):
    def view(request):
        _require(request, "use_disputes_console")
        from apps.payments.models import Dispute

        disputes = (
            Dispute.objects.filter(status=Dispute.Status.OPEN)
            .select_related("payment__buyer", "payment__seller", "conversation")
            .order_by("-overdue", "response_due_at")[:100]
        )
        return _page(site, request, "disputes.html", _("Disputes console"), disputes=disputes)

    return view


def selection_console(site):
    def view(request):
        _require(request, "use_selection_console")
        from apps.selection_france.models import SelectionOrder, Shipment

        O = SelectionOrder.Status  # noqa: E741
        orders = SelectionOrder.objects.select_related("buyer", "pickup_point")
        return _page(
            site,
            request,
            "selection.html",
            _("France Selection console"),
            to_order=orders.filter(status=O.TO_ORDER).order_by("created_at")[:100],
            in_france=orders.filter(status__in=[O.ORDERED, O.RECEIVED]).order_by("created_at")[
                :100
            ],
            shipments=Shipment.objects.exclude(status=Shipment.Status.ARRIVED).order_by(
                "-created_at"
            )[:30],
            at_points=orders.filter(status=O.ARRIVED).order_by("pickup_point", "created_at")[:100],
        )

    return view


# --- Prospects: import ---------------------------------------------------------------------------


class ImportForm(forms.Form):
    file = forms.FileField(label=_("CSV file"))
    source = forms.CharField(label=_("Source"), required=False, max_length=80)


def prospects_import(site):
    def view(request):
        if not (request.user.is_superuser or request.user.has_perm("backoffice.add_prospect")):
            raise PermissionDenied
        form = ImportForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            found = prospects.import_csv(
                form.cleaned_data["file"].read(),
                actor=request.user,
                source=form.cleaned_data["source"],
            )
            if found.get("error"):
                messages.error(request, _("A « name » column is needed."))
            else:
                messages.success(
                    request,
                    _("%(added)s added, %(skipped)s already known or empty.") % found,
                )
                return redirect(reverse("admin:backoffice_prospect_changelist"))
        return _page(
            site,
            request,
            "prospects_import.html",
            _("Import prospects"),
            form=form,
            count=Prospect.objects.count(),
        )

    return view


# --- Sign in as ----------------------------------------------------------------------------------


class ImpersonateForm(forms.Form):
    reason = forms.CharField(label=_("Why (written in the journal)"), max_length=200)


def impersonate_view(site):
    def view(request, user_id):
        User = get_user_model()
        target = get_object_or_404(User, pk=user_id)
        if not impersonation.can_impersonate(request.user, target):
            raise PermissionDenied
        form = ImpersonateForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            try:
                found, refresh = impersonation.start(
                    request.user, target, reason=form.cleaned_data["reason"]
                )
            except DomainError as exc:
                messages.error(request, exc.text())
                return redirect(reverse("admin:accounts_user_change", args=[target.pk]))
            response = HttpResponseRedirect(settings.SITE_URL)
            set_auth_cookies(response, refresh)
            response.set_cookie(
                impersonation.BANNER_COOKIE,
                # Read by the app to show the banner: only the first name (no number).
                f"{found.pk}|{quote((target.first_name or '')[:60])}",
                max_age=impersonation.minutes() * 60,
                path="/",
                samesite="Lax",
                secure=settings.AUTH_COOKIES["SECURE"],
                domain=settings.AUTH_COOKIES["DOMAIN"],
            )
            return response
        return _page(
            site,
            request,
            "impersonate.html",
            _("Sign in as %(name)s") % {"name": target},
            form=form,
            target=target,
            minutes=impersonation.minutes(),
            now=timezone.now(),
        )

    return view


def urls(site) -> list:
    wrap = site.admin_view
    return [
        path("2fa/", wrap(two_factor_view(site)), name="backoffice_2fa"),
        path("team/", wrap(team_view(site)), name="backoffice_team"),
        path("features/", wrap(flags_view(site)), name="backoffice_flags"),
        path("translations/", wrap(translations_view(site)), name="backoffice_translations"),
        path(
            "consoles/moderation/",
            wrap(moderation_console(site)),
            name="backoffice_moderation_console",
        ),
        path(
            "consoles/disputes/", wrap(disputes_console(site)), name="backoffice_disputes_console"
        ),
        path(
            "consoles/selection/",
            wrap(selection_console(site)),
            name="backoffice_selection_console",
        ),
        path("prospects/import/", wrap(prospects_import(site)), name="backoffice_prospects_import"),
        path(
            "impersonate/<uuid:user_id>/",
            wrap(impersonate_view(site)),
            name="backoffice_impersonate",
        ),
    ]
