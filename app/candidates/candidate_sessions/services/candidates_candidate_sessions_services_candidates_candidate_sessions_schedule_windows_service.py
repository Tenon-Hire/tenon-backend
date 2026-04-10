"""Application module for candidates candidate sessions services candidates candidate sessions schedule windows service workflows."""

from __future__ import annotations

from datetime import time

from app.candidates.candidate_sessions.services.scheduling.candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_service import (
    derive_day_windows,
    serialize_day_windows,
)


def _derive_serialized_day_windows(
    *,
    trial,
    scheduled_start_at_utc,
    normalized_timezone: str,
) -> list[dict[str, str | int]]:
    window_start, window_end = (
        getattr(trial, "day_window_start_local", None) or time(hour=9),
        getattr(trial, "day_window_end_local", None) or time(hour=17),
    )
    day_windows = derive_day_windows(
        scheduled_start_at_utc=scheduled_start_at_utc,
        candidate_tz=normalized_timezone,
        day_window_start_local=window_start,
        day_window_end_local=window_end,
        overrides=getattr(trial, "day_window_overrides_json", None),
        overrides_enabled=bool(getattr(trial, "day_window_overrides_enabled", False)),
        total_days=5,
    )
    return serialize_day_windows(day_windows)


__all__ = ["_derive_serialized_day_windows"]
