from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import FeatureFlag, PlatformSetting
from .selectors import flag_cache_key, setting_cache_key


def _invalidate(cache_key: str) -> None:
    # Delete now, and again after commit so a concurrent read cannot re-cache stale data.
    cache.delete(cache_key)
    transaction.on_commit(lambda: cache.delete(cache_key))


@receiver(pre_save, sender=PlatformSetting)
@receiver(pre_save, sender=FeatureFlag)
def invalidate_renamed_key(sender, instance, **kwargs):
    old_key = sender.objects.filter(pk=instance.pk).values_list("key", flat=True).first()
    if old_key and old_key != instance.key:
        key_fn = setting_cache_key if sender is PlatformSetting else flag_cache_key
        _invalidate(key_fn(old_key))


@receiver([post_save, post_delete], sender=PlatformSetting)
def invalidate_setting(sender, instance, **kwargs):
    _invalidate(setting_cache_key(instance.key))


@receiver([post_save, post_delete], sender=FeatureFlag)
def invalidate_flag(sender, instance, **kwargs):
    _invalidate(flag_cache_key(instance.key))


@receiver(m2m_changed, sender=FeatureFlag.countries.through)
def invalidate_flag_countries(sender, instance, **kwargs):
    if isinstance(instance, FeatureFlag):
        _invalidate(flag_cache_key(instance.key))
    else:
        for key in FeatureFlag.objects.filter(countries=instance).values_list("key", flat=True):
            _invalidate(flag_cache_key(key))
