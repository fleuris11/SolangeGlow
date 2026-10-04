from modeltranslation.translator import TranslationOptions, register

from .models import NotificationTemplate


@register(NotificationTemplate)
class NotificationTemplateTranslationOptions(TranslationOptions):
    fields = ("title", "body")
