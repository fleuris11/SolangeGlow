import factory

from apps.core.models import Country, Currency, FeatureFlag, PlatformSetting


class CurrencyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Currency
        django_get_or_create = ("code",)

    code = "XOF"
    name = "Franc CFA"
    symbol = "FCFA"
    decimal_places = 0


class CountryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Country
        django_get_or_create = ("code",)

    code = "BJ"
    name = "Bénin"
    phone_prefix = "+229"
    default_currency = factory.SubFactory(CurrencyFactory)
    timezone = "Africa/Porto-Novo"


class PlatformSettingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PlatformSetting

    key = factory.Sequence(lambda n: f"test.setting_{n}")
    value_type = PlatformSetting.ValueType.INTEGER
    value = "3"
    country = None


class FeatureFlagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FeatureFlag

    key = factory.Sequence(lambda n: f"flag-{n}")
    name = factory.Sequence(lambda n: f"Flag {n}")
    is_enabled = True
