from modeltranslation.translator import TranslationOptions, register

from .models import Plan


@register(Plan)
class PlanTranslationOptions(TranslationOptions):
    fields = ("name", "description")
