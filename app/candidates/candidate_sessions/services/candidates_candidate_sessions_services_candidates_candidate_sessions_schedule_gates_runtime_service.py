"""Application module for candidates candidate sessions services candidates candidate sessions schedule gates runtime service workflows."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from app.candidates.candidate_sessions.services.scheduling.candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_service import (
    coerce_utc_datetime,
)


def require_active_window_impl(
    candidate_session,
    task,
    *,
    now: datetime | None = None,
    compute_task_window: Callable[..., object],
    coerce_task_day_index: Callable[..., int | None],
    serialize_optional_datetime: Callable[[datetime | None], str | None],
    build_schedule_invalid_window_error: Callable[..., Exception],
    build_task_window_closed_error: Callable[..., Exception],
    logger: logging.Logger,
) -> None:
    """Require active window impl."""
    task_window = compute_task_window(candidate_session, task, now_utc=now)
    if task_window.is_open:
        return
    if task_window.window_start_at is None or task_window.window_end_at is None:
        logger.warning(
            "Task window config invalid candidateSessionId=%s taskId=%s dayIndex=%s now=%s windowStartAt=%s windowEndAt=%s",
            getattr(candidate_session, "id", None),
            getattr(task, "id", None),
            coerce_task_day_index(task),
            serialize_optional_datetime(task_window.now),
            serialize_optional_datetime(task_window.window_start_at),
            serialize_optional_datetime(task_window.window_end_at),
        )
        raise build_schedule_invalid_window_error(
            candidate_session, task, task_window=task_window
        )
    logger.info(
        "Task window gate blocked candidateSessionId=%s taskId=%s now=%s windowStartAt=%s windowEndAt=%s",
        getattr(candidate_session, "id", None),
        getattr(task, "id", None),
        serialize_optional_datetime(task_window.now),
        serialize_optional_datetime(task_window.window_start_at),
        serialize_optional_datetime(task_window.window_end_at),
    )
    raise build_task_window_closed_error(
        candidate_session, task, task_window=task_window
    )


def is_schedule_started_for_content_impl(
    candidate_session,
    *,
    now: datetime | None = None,
    compute_day1_window: Callable[..., tuple[datetime | None, datetime | None]],
) -> bool:
    """Return whether schedule started for content impl."""
    resolved_now = coerce_utc_datetime(now or datetime.now(UTC))
    window_start_at, _ = compute_day1_window(candidate_session)
    return window_start_at is not None and resolved_now >= window_start_at


def ensure_schedule_started_for_content_impl(
    candidate_session,
    *,
    now: datetime | None = None,
    normalize_optional_datetime: Callable[[datetime | None], datetime | None],
    serialize_optional_datetime: Callable[[datetime | None], str | None],
    compute_day1_window: Callable[..., tuple[datetime | None, datetime | None]],
    is_schedule_started_for_content: Callable[..., bool],
    build_schedule_not_started_error: Callable[..., Exception],
    logger: logging.Logger,
) -> None:
    """Ensure schedule started for content impl."""
    resolved_now = coerce_utc_datetime(now or datetime.now(UTC))
    window_start_at, window_end_at = compute_day1_window(candidate_session)
    if is_schedule_started_for_content(candidate_session, now=resolved_now):
        return
    scheduled_start_at = normalize_optional_datetime(
        getattr(candidate_session, "scheduled_start_at", None)
    )
    logger.info(
        "Candidate schedule gate blocked candidateSessionId=%s scheduledStartAt=%s",
        getattr(candidate_session, "id", None),
        serialize_optional_datetime(scheduled_start_at),
    )
    raise build_schedule_not_started_error(
        candidate_session, window_start_at, window_end_at
    )


__all__ = [
    "ensure_schedule_started_for_content_impl",
    "is_schedule_started_for_content_impl",
    "require_active_window_impl",
]
