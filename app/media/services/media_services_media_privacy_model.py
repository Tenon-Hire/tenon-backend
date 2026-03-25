from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MediaRetentionPurgeResult:
    scanned_count: int
    purged_count: int
    failed_count: int
    purged_recording_ids: list[int]
