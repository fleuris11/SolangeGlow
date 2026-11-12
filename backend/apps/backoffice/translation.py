from modeltranslation.translator import TranslationOptions, register

from .models import ProspectEmailTemplate


@register(ProspectEmailTemplate)
class ProspectEmailTemplateTranslationOptions(TranslationOptions):
    fields = ("subject", "body")
