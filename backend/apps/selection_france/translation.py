from modeltranslation.translator import TranslationOptions, register

from .models import SelectionCategory


@register(SelectionCategory)
class SelectionCategoryTranslationOptions(TranslationOptions):
    fields = ("name",)
