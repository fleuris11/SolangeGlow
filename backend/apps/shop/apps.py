from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _

SHOP_GROUP = "Shop review"
SHOP_PERMISSIONS = [
    "view_product",
    "change_product",
    "review_product",
    "view_forbiddenterm",
    "add_forbiddenterm",
    "change_forbiddenterm",
    "delete_forbiddenterm",
    "view_order",
]


def create_group(sender, **kwargs):
    """« Shop review » checks the doubtful products and edits the forbidden words."""
    from django.contrib.auth.models import Group, Permission

    group, _created = Group.objects.get_or_create(name=SHOP_GROUP)
    group.permissions.add(
        *Permission.objects.filter(content_type__app_label="shop", codename__in=SHOP_PERMISSIONS)
    )


class ShopConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.shop"
    verbose_name = _("Shop")

    def ready(self):
        from apps.messaging import shares
        from apps.payments import services as payment_services
        from apps.social import eligibility, products

        from . import links
        from .services import orders

        post_migrate.connect(create_group, sender=self)
        payment_services.listen("order", orders.on_payment_change, may_cancel=orders.may_cancel)
        eligibility.register(links.OrderEligibility())
        shares.register("product", links.share_product)
        products.register(links.owns_product, links.post_product_card)
