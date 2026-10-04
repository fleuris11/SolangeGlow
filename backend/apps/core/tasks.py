"""Celery discovers tasks in <app>.tasks: expose the ones living in sub-packages."""

from .media.tasks import process_media_asset

__all__ = ["process_media_asset"]
