"""Turns an uploaded original into ready-to-serve variants. Runs in a Celery task."""

from __future__ import annotations

import tempfile
from pathlib import Path

from django.core.files import File
from django.utils import timezone

from apps.core.selectors import get_setting

from . import ffmpeg, images
from .models import MediaAsset
from .storage import private_storage, public_storage


class Rejected(Exception):
    """The file is not acceptable (wrong type, too long). Not retried."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _target_storage(asset: MediaAsset):
    return (
        public_storage() if asset.visibility == MediaAsset.Visibility.PUBLIC else private_storage()
    )


def _saver(asset: MediaAsset):
    storage = _target_storage(asset)
    folder = f"{asset.kind}/{asset.pk}"

    def save(name, content):
        return storage.save(f"{folder}/{name}", content)

    return save


def _read_original(asset: MediaAsset) -> bytes:
    with asset.original.open("rb") as handle:
        return handle.read()


def process_image(asset: MediaAsset) -> None:
    try:
        image = images.open_image(_read_original(asset))
    except images.InvalidImage as exc:
        raise Rejected("invalid_image") from exc
    asset.width, asset.height = image.size
    asset.blurhash = images.compute_blurhash(image)
    asset.variants = images.render_variants(image, _saver(asset))


def _probe(path: Path) -> dict:
    try:
        return ffmpeg.probe(str(path))
    except ffmpeg.MediaToolError as exc:
        raise Rejected("unreadable") from exc


def _check_duration(asset: MediaAsset, seconds: float, setting: str, default: int) -> None:
    maximum = int(get_setting(setting, default=default))
    if seconds <= 0:
        raise Rejected("unreadable")
    if seconds > maximum:
        raise Rejected("too_long")


def _upload(save, name: str, path: Path, content_type: str) -> dict:
    with path.open("rb") as handle:
        stored = save(name, File(handle))
    return {"path": stored, "bytes": path.stat().st_size, "content_type": content_type}


def process_video(asset: MediaAsset) -> None:
    save = _saver(asset)
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "source"
        source.write_bytes(_read_original(asset))
        info = _probe(source)
        if not info["has_video"]:
            raise Rejected("not_a_video")
        _check_duration(asset, info["duration"], "media.video_max_seconds", 600)
        asset.duration_seconds = info["duration"]
        asset.width, asset.height = info["width"], info["height"]

        qualities = get_setting(
            "media.video_qualities",
            default={
                "low": {"height": 360, "crf": 30, "audio": "64k"},
                "medium": {"height": 720, "crf": 26, "audio": "96k"},
            },
        )
        variants = {}
        for name, quality in qualities.items():
            output = Path(tmp) / f"{name}.mp4"
            arguments = [
                "-i",
                str(source),
                # Even dimensions (H.264), never upscaled.
                "-vf",
                f"scale=-2:'trunc(min({int(quality['height'])},ih)/2)*2'",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                str(int(quality["crf"])),
                "-profile:v",
                "main",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
            ]
            if info["has_audio"]:
                arguments += ["-c:a", "aac", "-b:a", str(quality["audio"]), "-ac", "2"]
            else:
                arguments += ["-an"]
            ffmpeg.run([*arguments, str(output)])
            variants[name] = _upload(save, f"{name}.mp4", output, "video/mp4")

        poster = Path(tmp) / "poster.jpg"
        moment = min(1.0, info["duration"] / 2)
        ffmpeg.run(["-ss", f"{moment:.2f}", "-i", str(source), "-frames:v", "1", str(poster)])
        image = images.open_image(poster.read_bytes())
        asset.blurhash = images.compute_blurhash(image)
        variants.update(images.render_variants(image, save, prefix="poster_"))
        asset.variants = variants


def process_audio(asset: MediaAsset) -> None:
    save = _saver(asset)
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "source"
        source.write_bytes(_read_original(asset))
        info = _probe(source)
        if not info["has_audio"]:
            raise Rejected("not_audio")
        _check_duration(asset, info["duration"], "media.audio_max_seconds", 120)
        asset.duration_seconds = info["duration"]
        output = Path(tmp) / "voice.webm"
        bitrate = str(get_setting("media.audio_bitrate", default="32k"))
        ffmpeg.run(
            ["-i", str(source), "-vn", "-c:a", "libopus", "-b:a", bitrate, "-ac", "1", str(output)]
        )
        asset.variants = {"voice": _upload(save, "voice.webm", output, "audio/webm")}


PIPELINES = {
    MediaAsset.Kind.IMAGE: process_image,
    MediaAsset.Kind.VIDEO: process_video,
    MediaAsset.Kind.AUDIO: process_audio,
}


def process(asset: MediaAsset) -> None:
    """Runs the pipeline of the asset kind and records the outcome on the asset."""
    asset.status = MediaAsset.Status.PROCESSING
    asset.save(update_fields=["status", "updated_at"])
    try:
        PIPELINES[asset.kind](asset)
    except Rejected as exc:
        asset.status = MediaAsset.Status.REJECTED
        asset.error = exc.code
        asset.save()
        return
    asset.status = MediaAsset.Status.READY
    asset.error = ""
    asset.processed_at = timezone.now()
    asset.save()


def remove_files(asset: MediaAsset) -> None:
    storage = _target_storage(asset)
    for variant in (asset.variants or {}).values():
        path = variant.get("path")
        if path and storage.exists(path):
            storage.delete(path)
    if asset.original:
        asset.original.delete(save=False)
