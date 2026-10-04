"""Thin wrappers around ffprobe and ffmpeg (installed in the backend and worker image)."""

from __future__ import annotations

import json
import subprocess

from apps.core.selectors import get_setting


class MediaToolError(Exception):
    pass


def _timeout() -> int:
    return int(get_setting("media.ffmpeg_timeout_seconds", default=600))


def probe(path: str) -> dict:
    """Duration and streams of a media file."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type,width,height",
                "-of",
                "json",
                path,
            ],
            capture_output=True,
            check=True,
            timeout=60,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        raise MediaToolError("ffprobe failed") from exc
    data = json.loads(result.stdout or b"{}")
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    return {
        "duration": float(data.get("format", {}).get("duration") or 0),
        "has_video": video is not None,
        "has_audio": audio is not None,
        "width": video.get("width") if video else None,
        "height": video.get("height") if video else None,
    }


def run(arguments: list[str]) -> None:
    try:
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *arguments],
            capture_output=True,
            check=True,
            timeout=_timeout(),
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        raise MediaToolError("ffmpeg failed") from exc
