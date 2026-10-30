from modeltranslation.translator import TranslationOptions, register

from .models import Banner, FaqItem, Page


@register(Page)
class PageTranslationOptions(TranslationOptions):
    fields = ("title", "summary", "body")


@register(Banner)
class BannerTranslationOptions(TranslationOptions):
    fields = ("title", "text", "cta")


@register(FaqItem)
class FaqItemTranslationOptions(TranslationOptions):
    fields = ("question", "answer")
