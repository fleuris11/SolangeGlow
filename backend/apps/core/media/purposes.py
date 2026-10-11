"""What each module may upload. A module adds its uses here (kinds accepted, visibility)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Duration:
    """Length limits of a video or a voice note, read from platform settings."""

    min_setting: str | None = None
    min_default: int = 0
    max_setting: str | None = None
    max_default: int | None = None


@dataclass(frozen=True)
class Purpose:
    kinds: tuple[str, ...]
    visibility: str
    duration: Duration | None = None


PURPOSES: dict[str, Purpose] = {
    "avatar": Purpose(("image",), "public"),
    "post": Purpose(("image", "video"), "public"),
    "voice_note": Purpose(("audio",), "private"),
    "identity_document": Purpose(("image",), "private"),
    # Pros (module 1): showcase pictures, voice notes heard by every visitor, portfolio.
    "pro_photo": Purpose(("image",), "public"),
    "pro_cover": Purpose(("image",), "public"),
    "pro_voice": Purpose(
        ("audio",), "public", Duration(max_setting="pros.voice_note_max_seconds", max_default=120)
    ),
    "service_photo": Purpose(("image",), "public"),
    "portfolio": Purpose(("image", "video"), "public"),
    "itinerary_video": Purpose(
        ("video",),
        "public",
        Duration(
            min_setting="pros.itinerary_video_min_seconds",
            min_default=30,
            max_setting="pros.itinerary_video_max_seconds",
            max_default=60,
        ),
    ),
}
