from modeltranslation.translator import TranslationOptions, register

from .models import Country, Currency, FeatureFlag, PlatformSetting


@register(Currency)
class CurrencyTranslationOptions(TranslationOptions):
    fields = ("name",)


@register(Country)
class CountryTranslationOptions(TranslationOptions):
    fields = ("name",)


@register(PlatformSetting)
class PlatformSettingTranslationOptions(TranslationOptions):
    fields = ("description",)


@register(FeatureFlag)
class FeatureFlagTranslationOptions(TranslationOptions):
    fields = ("name", "description")
