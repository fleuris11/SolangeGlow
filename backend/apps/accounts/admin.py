from django import forms
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.widgets import UnfoldAdminCheckboxSelectMultipleWidget

from apps.core.choices import Role

from .models import User


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


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = ["__str__", "email", "phone", "country", "roles", "is_active", "created_at"]
    list_filter = ["is_active", "is_staff", "country", "preferred_language", "created_at"]
    search_fields = ["email", "phone", "first_name", "last_name"]
    ordering = ["-created_at"]
    readonly_fields = ["last_login", "created_at", "updated_at"]
    autocomplete_fields = ["country", "preferred_currency"]

    fieldsets = (
        (None, {"fields": ("email", "phone", "password")}),
        (_("Profile"), {"fields": ("first_name", "last_name", "country")}),
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
        (_("Dates"), {"fields": ("last_login", "created_at", "updated_at")}),
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


admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass
