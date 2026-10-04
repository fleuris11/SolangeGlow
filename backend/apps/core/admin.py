from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django_celery_beat.admin import ClockedScheduleAdmin as BaseClockedScheduleAdmin
from django_celery_beat.admin import CrontabScheduleAdmin as BaseCrontabScheduleAdmin
from django_celery_beat.admin import PeriodicTaskAdmin as BasePeriodicTaskAdmin
from django_celery_beat.admin import PeriodicTaskForm, TaskSelectWidget
from django_celery_beat.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    SolarSchedule,
)
from modeltranslation.admin import TabbedTranslationAdmin
from unfold.decorators import display
from unfold.widgets import UnfoldAdminCheckboxSelectMultipleWidget, UnfoldAdminSelectWidget

from .audit.admin import AuditedModelAdmin
from .choices import Role
from .media import admin as media_admin  # noqa: F401  (registers the media screens)
from .models import Country, Currency, FeatureFlag, PlatformSetting


@admin.register(Currency)
class CurrencyAdmin(AuditedModelAdmin, TabbedTranslationAdmin):
    list_display = ["code", "name", "symbol", "decimal_places", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(Country)
class CountryAdmin(AuditedModelAdmin, TabbedTranslationAdmin):
    list_display = ["code", "name", "phone_prefix", "default_currency", "default_language"]
    list_filter = ["is_active", "default_currency"]
    search_fields = ["code", "name"]
    autocomplete_fields = ["default_currency"]


@admin.register(PlatformSetting)
class PlatformSettingAdmin(AuditedModelAdmin, TabbedTranslationAdmin):
    list_display = ["key", "scope", "value", "value_type", "updated_at"]
    list_filter = ["value_type", "country"]
    search_fields = ["key", "description"]
    autocomplete_fields = ["country"]
    readonly_fields = ["created_at", "updated_at"]
    fields = ["key", "country", "value_type", "value", "description", "created_at", "updated_at"]

    @display(description=_("scope"))
    def scope(self, obj):
        return obj.country.code if obj.country_id else _("All countries")


class FeatureFlagForm(forms.ModelForm):
    roles = forms.MultipleChoiceField(
        label=_("roles"),
        choices=Role.choices,
        required=False,
        widget=UnfoldAdminCheckboxSelectMultipleWidget,
        help_text=_("Leave empty to enable for every role."),
    )

    class Meta:
        model = FeatureFlag
        fields = ["key", "name", "description", "is_enabled", "countries", "roles"]


@admin.register(FeatureFlag)
class FeatureFlagAdmin(AuditedModelAdmin, TabbedTranslationAdmin):
    form = FeatureFlagForm
    list_display = ["key", "name", "is_enabled", "updated_at"]
    list_filter = ["is_enabled", "countries"]
    list_editable = ["is_enabled"]
    search_fields = ["key", "name"]
    filter_horizontal = ["countries"]


# --- Celery Beat, restyled with Unfold ------------------------------------------

for model in (PeriodicTask, IntervalSchedule, CrontabSchedule, SolarSchedule, ClockedSchedule):
    admin.site.unregister(model)


class UnfoldTaskSelectWidget(UnfoldAdminSelectWidget, TaskSelectWidget):
    pass


class UnfoldPeriodicTaskForm(PeriodicTaskForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["task"].widget = UnfoldTaskSelectWidget()


@admin.register(PeriodicTask)
class PeriodicTaskAdmin(BasePeriodicTaskAdmin, AuditedModelAdmin):
    form = UnfoldPeriodicTaskForm


@admin.register(IntervalSchedule)
class IntervalScheduleAdmin(AuditedModelAdmin):
    pass


@admin.register(CrontabSchedule)
class CrontabScheduleAdmin(BaseCrontabScheduleAdmin, AuditedModelAdmin):
    pass


@admin.register(SolarSchedule)
class SolarScheduleAdmin(AuditedModelAdmin):
    pass


@admin.register(ClockedSchedule)
class ClockedScheduleAdmin(BaseClockedScheduleAdmin, AuditedModelAdmin):
    pass
