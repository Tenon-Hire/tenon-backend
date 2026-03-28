"""Application module for candidates candidate sessions services candidates candidate sessions schedule fields service workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.candidates.candidate_sessions.services.scheduling.candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_service import (
    coerce_utc_datetime,
    derive_current_day_window,
    deserialize_day_windows,
)


def _normalize_optional_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return coerce_utc_datetime(value)


def schedule_payload_for_candidate_session(
    candidate_session: Any, *, now_utc: datetime | None = None
) -> dict[str, Any]:
    """Schedule payload for candidate session."""
    day_windows = deserialize_day_windows(
        getattr(candidate_session, "day_windows_json", None)
    )
    resolved_now = coerce_utc_datetime(now_utc or datetime.now(UTC))
    return {
        "scheduledStartAt": _normalize_optional_datetime(
            getattr(candidate_session, "scheduled_start_at", None)
        ),
        "candidateTimezone": getattr(candidate_session, "candidate_timezone", None),
        "dayWindows": day_windows,
        "scheduleLockedAt": _normalize_optional_datetime(
            getattr(candidate_session, "schedule_locked_at", None)
        ),
        "currentDayWindow": derive_current_day_window(
            day_windows, now_utc=resolved_now
        ),
    }


__all__ = ["schedule_payload_for_candidate_session"]
