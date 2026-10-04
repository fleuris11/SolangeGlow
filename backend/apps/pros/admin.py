from django.contrib import admin
from modeltranslation.admin import TabbedTranslationAdmin
from unfold.admin import ModelAdmin

from .models import ProProfile, Trade


@admin.register(Trade)
class TradeAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = ["name", "key", "icon", "position", "is_active"]
    list_editable = ["position", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["key", "name"]


@admin.register(ProProfile)
class ProProfileAdmin(ModelAdmin):
    list_display = ["user", "kind", "created_at"]
    list_filter = ["kind", "trades"]
    search_fields = ["user__email", "user__phone", "user__first_name"]
    autocomplete_fields = ["user"]
    filter_horizontal = ["trades"]
