from apps.core import demo_photos
from apps.social import demo_art


def test_every_listed_photo_exists():
    names = {name for names in demo_photos.TRADES.values() for name in names}
    names |= set(demo_photos.PRODUCTS.values()) | set(demo_photos.PORTRAITS)
    missing = [name for name in names if not (demo_photos.FOLDER / f"{name}.jpg").exists()]
    assert missing == []


def test_a_look_is_a_real_jpeg_chosen_by_trade_and_seed():
    first = demo_photos.look("a", "braids")
    assert first[:2] == b"\xff\xd8"
    assert demo_photos.look("a", "braids") == first


def test_the_before_picture_differs_from_the_after_picture():
    assert demo_photos.look("a", "hair", stage="before") != demo_photos.look("a", "hair")


def test_an_unknown_product_has_no_photo():
    assert demo_photos.product("a", "unknown") is None
    assert demo_photos.product("a", "palette")[:2] == b"\xff\xd8"


def test_demo_art_falls_back_on_a_drawing(monkeypatch):
    monkeypatch.setattr(demo_photos, "look", lambda *args, **kwargs: None)
    assert demo_art.picture("a", "nails")[:2] == b"\xff\xd8"
