"""Application module for candidates candidate sessions services candidates candidate sessions schedule gates compute service workflows."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_schedule_gates_model import (
    TaskWindow,
)
from app.candidates.candidate_sessions.services.scheduling.candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_service import (
    coerce_utc_datetime,
)


def _closed_window(now: datetime) -> TaskWindow:
    return TaskWindow(
        window_start_at=None,
        window_end_at=None,
        next_open_at=None,
        is_open=False,
        now=now,
    )


def compute_day1_window_impl(
    candidate_session,
    *,
    load_day_windows: Callable[..., list[dict[str, Any]]],
    pick_day1_window: Callable[[list[dict[str, Any]]], dict[str, Any] | None],
    normalize_optional_datetime: Callable[[datetime | None], datetime | None],
) -> tuple[datetime | None, datetime | None]:
    """Compute day1 window impl."""
    day_windows = load_day_windows(candidate_session, minimum_total_days=1)
    day1_window = pick_day1_window(day_windows)
    if day1_window is not None:
        return (
            normalize_optional_datetime(day1_window["windowStartAt"]),
            normalize_optional_datetime(day1_window["windowEndAt"]),
        )
    return normalize_optional_datetime(
        getattr(candidate_session, "scheduled_start_at", None)
    ), None


def compute_task_window_impl(
    candidate_session,
    task,
    *,
    now_utc: datetime | None = None,
    load_day_windows: Callable[..., list[dict[str, Any]]],
    coerce_task_day_index: Callable[[Any], int | None],
    window_for_day: Callable[[list[dict[str, Any]], int], dict[str, Any] | None],
    next_window_start_for_day: Callable[[list[dict[str, Any]], int], datetime | None],
    normalize_optional_datetime: Callable[[datetime | None], datetime | None],
) -> TaskWindow:
    """Compute task window impl."""
    resolved_now = coerce_utc_datetime(now_utc or datetime.now(UTC))
    day_index = coerce_task_day_index(task)
    if day_index is None:
        return _closed_window(resolved_now)
    day_windows = load_day_windows(
        candidate_session, minimum_total_days=max(5, day_index)
    )
    current_window = window_for_day(day_windows, day_index)
    if current_window is None:
        return _closed_window(resolved_now)
    window_start_at = normalize_optional_datetime(current_window["windowStartAt"])
    window_end_at = normalize_optional_datetime(current_window["windowEndAt"])
    if window_start_at is None or window_end_at is None:
        return TaskWindow(
            window_start_at=window_start_at,
            window_end_at=window_end_at,
            next_open_at=None,
            is_open=False,
            now=resolved_now,
        )
    is_open = window_start_at <= resolved_now < window_end_at
    next_open_at = None
    if resolved_now < window_start_at:
        next_open_at = window_start_at
    elif resolved_now >= window_end_at:
        next_open_at = next_window_start_for_day(day_windows, day_index)
    return TaskWindow(
        window_start_at=window_start_at,
        window_end_at=window_end_at,
        next_open_at=next_open_at,
        is_open=is_open,
        now=resolved_now,
    )


__all__ = ["compute_day1_window_impl", "compute_task_window_impl"]
