"""Worker handler for media retention purge jobs."""

from __future__ import annotations

from typing import Any

from app.integrations.storage_media import get_storage_media_provider
from app.media.services.media_services_media_privacy_service import (
    purge_expired_media_assets,
)
from app.media.services.media_services_media_retention_jobs_service import (
    MEDIA_RETENTION_PURGE_JOB_TYPE,
)
from app.shared.database import async_session_maker
from app.shared.utils.shared_utils_parsing_utils import parse_positive_int


async def handle_media_retention_purge(payload_json: dict[str, Any]) -> dict[str, Any]:
    """Run media retention purge through the shared worker."""
    retention_days = parse_positive_int(payload_json.get("retentionDays"))
    batch_limit = parse_positive_int(payload_json.get("batchLimit")) or 200
    async with async_session_maker() as db:
        result = await purge_expired_media_assets(
            db,
            storage_provider=get_storage_media_provider(),
            retention_days=retention_days,
            batch_limit=batch_limit,
        )
    return {
        "scannedCount": result.scanned_count,
        "purgedCount": result.purged_count,
        "skippedCount": result.skipped_count,
        "failedCount": result.failed_count,
    }


__all__ = ["MEDIA_RETENTION_PURGE_JOB_TYPE", "handle_media_retention_purge"]
