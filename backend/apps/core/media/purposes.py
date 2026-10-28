"""What each module may upload. A module adds its uses here (kinds accepted, visibility)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Duration:
    """Length limits of a video or a voice note, read from platform settings."""

    min_setting: str | None = None
    min_default: int = 0
    max_setting: str | None = None
    max_default: int | None = None
    # True: replaces the general limit of the kind instead of lowering it (long replays).
    replaces_general: bool = False


@dataclass(frozen=True)
class Purpose:
    kinds: tuple[str, ...]
    visibility: str
    duration: Duration | None = None
    # Size limit of this use (else the general limit of the kind, media.<kind>_max_bytes).
    max_bytes_setting: str | None = None
    max_bytes_default: int | None = None
    # False: written by the platform itself (replays), never sent through the media API.
    uploadable: bool = True


PURPOSES: dict[str, Purpose] = {
    "avatar": Purpose(("image",), "public"),
    # Social (module 2): posts, stories, reviews.
    "post": Purpose(
        ("image", "video"),
        "public",
        Duration(max_setting="social.video_max_seconds", max_default=90),
    ),
    "story": Purpose(
        ("image", "video"),
        "public",
        Duration(max_setting="social.story_video_max_seconds", max_default=30),
    ),
    "review_photo": Purpose(("image",), "public"),
    "review_voice": Purpose(
        ("audio",), "public", Duration(max_setting="reviews.voice_max_seconds", max_default=120)
    ),
    "voice_note": Purpose(
        ("audio",), "private", Duration(max_setting="messaging.voice_max_seconds", max_default=180)
    ),
    "message_photo": Purpose(("image",), "private"),
    "delivery_proof": Purpose(("image",), "private"),
    "dispute_evidence": Purpose(("image",), "private"),
    "identity_document": Purpose(("image",), "private"),
    # Pros (module 1): showcase pictures, voice notes heard by every visitor, portfolio.
    "pro_photo": Purpose(("image",), "public"),
    "pro_cover": Purpose(("image",), "public"),
    "pro_voice": Purpose(
        ("audio",), "public", Duration(max_setting="pros.voice_note_max_seconds", max_default=120)
    ),
    "service_photo": Purpose(("image",), "public"),
    "portfolio": Purpose(("image", "video"), "public"),
    # Shops (module 4): product pictures (bundles too), a short video, a voice description.
    "product_photo": Purpose(("image",), "public"),
    "product_video": Purpose(
        ("video",), "public", Duration(max_setting="shop.video_max_seconds", max_default=60)
    ),
    "product_voice": Purpose(
        ("audio",), "public", Duration(max_setting="pros.voice_note_max_seconds", max_default=120)
    ),
    # France Selection (module 6): catalogue pictures (team), a client's picture of a wish.
    "selection_photo": Purpose(("image",), "public"),
    "selection_request": Purpose(("image",), "private"),
    # Bookings (module 8): a picture of the result, in the pro's client file.
    "booking_result": Purpose(("image",), "private"),
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
    # Academy (module 7): course covers, lessons of 3 to 10 minutes, PDF resources.
    "course_cover": Purpose(("image",), "public"),
    "lesson_video": Purpose(
        ("video",),
        "private",
        Duration(
            min_setting="academy.lesson_min_seconds",
            min_default=180,
            max_setting="academy.lesson_max_seconds",
            max_default=600,
        ),
        max_bytes_setting="academy.lesson_max_bytes",
        max_bytes_default=500 * 1024 * 1024,
    ),
    # Lives (ADR-013): the recording of the host, written by LiveKit, kept a few days.
    "live_replay": Purpose(
        ("video",),
        "private",
        Duration(
            max_setting="live.replay_max_seconds",
            max_default=2 * 3600 + 600,
            replaces_general=True,
        ),
        uploadable=False,
    ),
    # Diaspora gifts (module 9): a voice or video message, a photo of the result.
    "gift_message": Purpose(
        ("audio", "video"),
        "private",
        Duration(max_setting="gifts.message_max_seconds", max_default=60),
    ),
    "gift_proof": Purpose(("image",), "private"),
    "course_resource": Purpose(
        ("document",),
        "private",
        max_bytes_setting="academy.resource_max_bytes",
        max_bytes_default=20 * 1024 * 1024,
    ),
}
