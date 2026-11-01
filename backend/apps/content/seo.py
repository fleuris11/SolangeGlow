"""What search engines may list: only what anyone can see (published, not hidden)."""

from __future__ import annotations

from apps.academy import selectors as academy
from apps.core.selectors import get_setting
from apps.pros.models import ProProfile
from apps.selection_france import selectors as selection
from apps.shop import selectors as shop

from .models import Page

KINDS = ("pros", "products", "selection", "courses", "pages")


def entries(kind: str) -> list[dict]:
    """Paths without the language (« /aicha/shop/robe »), most recent first."""
    most = int(get_setting("seo.sitemap_max", default=40_000))
    if kind == "pros":
        rows = ProProfile.objects.filter(status=ProProfile.Status.PUBLISHED)
        found = rows.order_by("-updated_at").values_list("slug", "updated_at")[:most]
        return [{"path": f"/{slug}", "updated_at": at} for slug, at in found]
    if kind == "products":
        found = (
            shop.on_sale()
            .order_by("-updated_at")
            .values_list("pro__slug", "slug", "updated_at")[:most]
        )
        return [{"path": f"/{pro}/shop/{slug}", "updated_at": at} for pro, slug, at in found]
    if kind == "selection":
        found = selection.on_sale().order_by("-updated_at").values_list("slug", "updated_at")
        return [{"path": f"/selection/{slug}", "updated_at": at} for slug, at in found[:most]]
    if kind == "courses":
        found = academy.published().order_by("-updated_at").values_list("slug", "updated_at")
        return [{"path": f"/academie/{slug}", "updated_at": at} for slug, at in found[:most]]
    found = Page.objects.filter(is_published=True).values_list("slug", "updated_at")
    return [{"path": f"/pages/{slug}", "updated_at": at} for slug, at in found]
