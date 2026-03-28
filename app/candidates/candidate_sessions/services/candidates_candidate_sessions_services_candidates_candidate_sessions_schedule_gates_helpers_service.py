"""Application module for candidates candidate sessions services candidates candidate sessions schedule gates helpers service workflows."""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

from app.candidates.candidate_sessions.services.scheduling.candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_service import (
    coerce_utc_datetime,
)

DEFAULT_WINDOW_START = time(hour=9, minute=0)
DEFAULT_WINDOW_END = time(hour=17, minute=0)


def _normalize_optional_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return coerce_utc_datetime(value).replace(microsecond=0)


def _serialize_optional_datetime(value: datetime | None) -> str | None:
    normalized = _normalize_optional_datetime(value)
    if normalized is None:
        return None
    return normalized.isoformat(timespec="seconds").replace("+00:00", "Z")


def _pick_day1_window(day_windows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not day_windows:
        return None
    ordered = sorted(day_windows, key=lambda item: int(item["dayIndex"]))
    for window in ordered:
        if int(window["dayIndex"]) == 1:
            return window
    return ordered[0]


def _window_for_day(
    day_windows: list[dict[str, Any]], day_index: int
) -> dict[str, Any] | None:
    for window in day_windows:
        if int(window["dayIndex"]) == day_index:
            return window
    return None


def _next_window_start_for_day(
    day_windows: list[dict[str, Any]], day_index: int
) -> datetime | None:
    for window in day_windows:
        if int(window["dayIndex"]) > day_index:
            return _normalize_optional_datetime(window["windowStartAt"])
    return None


def _coerce_task_day_index(task: Any) -> int | None:
    raw = getattr(task, "day_index", None)
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.strip().isdigit():
        return int(raw.strip())
    return None


__all__ = [
    "DEFAULT_WINDOW_END",
    "DEFAULT_WINDOW_START",
    "_coerce_task_day_index",
    "_next_window_start_for_day",
    "_normalize_optional_datetime",
    "_pick_day1_window",
    "_serialize_optional_datetime",
    "_window_for_day",
]
