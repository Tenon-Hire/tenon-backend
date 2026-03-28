"""Application module for candidates candidate sessions services candidates candidate sessions day close jobs payloads service workflows."""

from __future__ import annotations

from datetime import UTC, datetime


def _to_utc_z(value: datetime) -> str:
    normalized = value.astimezone(UTC).replace(microsecond=0)
    return normalized.isoformat().replace("+00:00", "Z")


def build_day_close_finalize_text_payload(
    *, candidate_session_id: int, task_id: int, day_index: int, window_end_at: datetime
) -> dict[str, object]:
    """Build day close finalize text payload."""
    return {
        "candidateSessionId": candidate_session_id,
        "taskId": task_id,
        "dayIndex": day_index,
        "windowEndAt": _to_utc_z(window_end_at),
    }


def build_day_close_enforcement_payload(
    *, candidate_session_id: int, task_id: int, day_index: int, window_end_at: datetime
) -> dict[str, object]:
    """Build day close enforcement payload."""
    return {
        "candidateSessionId": candidate_session_id,
        "taskId": task_id,
        "dayIndex": day_index,
        "windowEndAt": _to_utc_z(window_end_at),
    }


__all__ = [
    "build_day_close_enforcement_payload",
    "build_day_close_finalize_text_payload",
]
