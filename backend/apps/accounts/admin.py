from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.widgets import UnfoldAdminCheckboxSelectMultipleWidget

from apps.core.audit.admin import AuditedModelAdmin
from apps.core.choices import Role

from . import services
from .models import GuestIdentity, LoginEvent, OtpChallenge, SignupChannel, User


class RolesField(forms.MultipleChoiceField):
    def __init__(self, **kwargs):
        super().__init__(
            label=_("roles"),
            choices=Role.choices,
            widget=UnfoldAdminCheckboxSelectMultipleWidget,
            **kwargs,
        )


class UserAdminCreationForm(UserCreationForm):
    roles = RolesField(initial=[Role.CLIENT])

    class Meta:
        model = User
        fields = ("email", "phone", "roles")

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("email") and not cleaned.get("phone"):
            raise forms.ValidationError(_("Enter a phone number or an e-mail address."))
        return cleaned


class UserAdminChangeForm(UserChangeForm):
    roles = RolesField()

    class Meta:
        model = User
        fields = "__all__"


class RoleFilter(admin.SimpleListFilter):
    title = _("role")
    parameter_name = "role"

    def lookups(self, request, model_admin):
        return Role.choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(roles__contains=[self.value()])
        return queryset


class StatusFilter(admin.SimpleListFilter):
    title = _("status")
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return [
            ("active", _("Active")),
            ("suspended", _("Suspended")),
            ("deleted", _("Deleted")),
        ]

    def queryset(self, request, queryset):
        if self.value() == "active":
            return queryset.filter(is_active=True)
        if self.value() == "suspended":
            return queryset.filter(is_active=False, deleted_at__isnull=True)
        if self.value() == "deleted":
            return queryset.filter(deleted_at__isnull=False)
        return queryset


class LoginEventInline(TabularInline):
    model = LoginEvent
    extra = 0
    max_num = 0
    can_delete = False
    fields = ["created_at", "method", "channel", "success", "failure_reason", "ip_address"]
    readonly_fields = fields
    ordering = ["-created_at"]
    tab = True


@admin.register(User)
class UserAdmin(BaseUserAdmin, AuditedModelAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = [
        "__str__",
        "email",
        "phone",
        "country",
        "roles",
        "signup_channel",
        "is_active",
        "created_at",
    ]
    list_filter = [
        StatusFilter,
        RoleFilter,
        "country",
        "signup_channel",
        ("created_at", RangeDateFilter),
        "preferred_language",
        "is_staff",
    ]
    list_filter_submit = True
    search_fields = ["email", "phone", "first_name", "last_name"]
    ordering = ["-created_at"]
    readonly_fields = [
        "last_login",
        "created_at",
        "updated_at",
        "signup_channel",
        "phone_verified_at",
        "email_verified_at",
        "onboarded_at",
        "tokens_revoked_at",
        "deleted_at",
    ]
    autocomplete_fields = ["country", "preferred_currency"]
    actions = ["suspend_users", "reactivate_users"]

    fieldsets = (
        (None, {"fields": ("email", "phone", "password")}),
        (
            _("Profile"),
            {"fields": ("first_name", "last_name", "birth_date", "country", "city", "photo")},
        ),
        (
            _("Preferences"),
            {
                "fields": (
                    "preferred_language",
                    "preferred_currency",
                    "theme",
                    "text_size",
                    "data_saver",
                    "audio_mode",
                    "notify_whatsapp",
                    "notify_email",
                    "notify_push",
                )
            },
        ),
        (
            _("Roles and permissions"),
            {
                "fields": (
                    "roles",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            _("Dates"),
            {
                "fields": (
                    "signup_channel",
                    "phone_verified_at",
                    "email_verified_at",
                    "onboarded_at",
                    "last_login",
                    "tokens_revoked_at",
                    "deleted_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "phone", "roles", "password1", "password2"),
            },
        ),
    )

    def get_inlines(self, request, obj):
        # The sign-in journal only exists for an existing account.
        return [LoginEventInline] if obj else []

    def save_model(self, request, obj, form, change):
        if not change:
            obj.signup_channel = SignupChannel.ADMIN
        super().save_model(request, obj, form, change)

    @admin.action(description=_("Suspend the selected accounts"))
    def suspend_users(self, request, queryset):
        count = 0
        for user in queryset.filter(is_active=True).exclude(pk=request.user.pk):
            services.suspend(user, actor=request.user)
            self.log_change(request, user, _("Suspended"))
            count += 1
        self.message_user(
            request,
            ngettext("%(count)d account suspended.", "%(count)d accounts suspended.", count)
            % {"count": count},
            messages.SUCCESS,
        )

    @admin.action(description=_("Reactivate the selected accounts"))
    def reactivate_users(self, request, queryset):
        count = 0
        for user in queryset.filter(is_active=False, deleted_at__isnull=True):
            services.reactivate(user, actor=request.user)
            self.log_change(request, user, _("Reactivated"))
            count += 1
        self.message_user(
            request,
            ngettext("%(count)d account reactivated.", "%(count)d accounts reactivated.", count)
            % {"count": count},
            messages.SUCCESS,
        )


@admin.register(LoginEvent)
class LoginEventAdmin(ModelAdmin):
    list_display = [
        "created_at",
        "user",
        "method",
        "channel",
        "success",
        "failure_reason",
        "ip_address",
    ]
    list_filter = ["success", "method", "channel", ("created_at", RangeDateFilter)]
    list_filter_submit = True
    search_fields = ["user__email", "user__phone", "ip_address"]
    readonly_fields = [f.name for f in LoginEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(OtpChallenge)
class OtpChallengeAdmin(ModelAdmin):
    """Codes sent. The code itself is never stored, so it can never be shown."""

    list_display = [
        "created_at",
        "destination_kind",
        "channel",
        "country_code",
        "attempts",
        "verified_at",
    ]
    list_filter = ["destination_kind", "channel", "country_code", ("created_at", RangeDateFilter)]
    list_filter_submit = True
    fields = [
        "destination_kind",
        "channel",
        "country_code",
        "expires_at",
        "attempts",
        "max_attempts",
        "verified_at",
        "created_at",
    ]
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(GuestIdentity)
class GuestIdentityAdmin(AuditedModelAdmin):
    list_display = ["first_name", "phone", "user", "converted_at", "created_at"]
    list_filter = [("created_at", RangeDateFilter)]
    list_filter_submit = True
    search_fields = ["first_name", "phone"]
    readonly_fields = ["user", "converted_at", "created_at"]


admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, AuditedModelAdmin):
    pass
