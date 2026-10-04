"""What each module may upload. A module adds its uses here (kinds accepted, visibility)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Purpose:
    kinds: tuple[str, ...]
    visibility: str


PURPOSES: dict[str, Purpose] = {
    "avatar": Purpose(("image",), "public"),
    "post": Purpose(("image", "video"), "public"),
    "itinerary_video": Purpose(("video",), "public"),
    "voice_note": Purpose(("audio",), "private"),
    "identity_document": Purpose(("image",), "private"),
}
