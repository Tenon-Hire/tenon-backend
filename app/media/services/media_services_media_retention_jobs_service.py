"""Shared job helpers for media retention purge."""

from __future__ import annotations

from app.config import settings

MEDIA_RETENTION_PURGE_JOB_TYPE = "media_retention_purge"
MEDIA_RETENTION_PURGE_MAX_ATTEMPTS = 3


def media_retention_purge_idempotency_key() -> str:
    """Return stable idempotency key for the singleton retention purge job."""
    return "media_retention_purge:global"


def build_media_retention_purge_payload(
    *, batch_limit: int = 200, retention_days: int | None = None
) -> dict[str, int]:
    """Build a privacy-safe media retention purge job payload."""
    payload = {"batchLimit": max(1, int(batch_limit))}
    if retention_days is not None:
        payload["retentionDays"] = int(retention_days)
    else:
        payload["retentionDays"] = int(settings.storage_media.MEDIA_RETENTION_DAYS)
    return payload


__all__ = [
    "MEDIA_RETENTION_PURGE_JOB_TYPE",
    "MEDIA_RETENTION_PURGE_MAX_ATTEMPTS",
    "build_media_retention_purge_payload",
    "media_retention_purge_idempotency_key",
]
