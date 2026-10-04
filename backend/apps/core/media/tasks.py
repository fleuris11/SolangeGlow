import logging

from celery import shared_task

from .ffmpeg import MediaToolError
from .models import MediaAsset
from .processing import process

logger = logging.getLogger("solangeglow.media")


@shared_task(bind=True, max_retries=2, default_retry_delay=30, acks_late=True)
def process_media_asset(self, asset_id: str) -> str:
    """Idempotent: an asset already processed (ready or refused) is left as is."""
    asset = MediaAsset.objects.filter(pk=asset_id).first()
    if asset is None:
        return "missing"
    if asset.status in (MediaAsset.Status.READY, MediaAsset.Status.REJECTED):
        return asset.status
    try:
        process(asset)
    except (MediaToolError, OSError) as exc:  # temporary: storage or ffmpeg trouble
        logger.warning("Media %s processing failed: %s", asset_id, exc)
        if self.request.retries >= self.max_retries:
            asset.status = MediaAsset.Status.FAILED
            asset.error = "processing_failed"
            asset.save(update_fields=["status", "error", "updated_at"])
            return asset.status
        raise self.retry(exc=exc) from exc
    return asset.status
