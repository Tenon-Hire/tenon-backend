"""Application module for media services media privacy model workflows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MediaRetentionPurgeResult:
    """Represent media retention purge result data and behavior."""

    scanned_count: int
    purged_count: int
    skipped_count: int
    failed_count: int
    purged_recording_ids: list[int]
