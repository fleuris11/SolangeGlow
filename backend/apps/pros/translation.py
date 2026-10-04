from modeltranslation.translator import TranslationOptions, register

from .models import Trade


@register(Trade)
class TradeTranslationOptions(TranslationOptions):
    fields = ("name",)
