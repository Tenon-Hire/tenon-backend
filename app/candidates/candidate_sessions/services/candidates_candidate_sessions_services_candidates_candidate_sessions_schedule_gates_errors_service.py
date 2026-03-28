"""Application module for candidates candidate sessions services candidates candidate sessions schedule gates errors service workflows."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from fastapi import status

from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_schedule_gates_model import (
    TaskWindow,
)
from app.shared.utils.shared_utils_errors_utils import (
    SCHEDULE_INVALID_WINDOW,
    SCHEDULE_NOT_STARTED,
    TASK_WINDOW_CLOSED,
    ApiError,
)


def build_task_window_closed_error(
    _candidate_session,
    _task,
    *,
    task_window: TaskWindow,
    serialize_optional_datetime: Callable[[datetime | None], str | None],
) -> ApiError:
    """Build task window closed error."""
    return ApiError(
        status_code=status.HTTP_409_CONFLICT,
        detail="Task is closed outside the scheduled window.",
        error_code=TASK_WINDOW_CLOSED,
        retryable=True,
        details={
            "windowStartAt": serialize_optional_datetime(task_window.window_start_at),
            "windowEndAt": serialize_optional_datetime(task_window.window_end_at),
            "nextOpenAt": serialize_optional_datetime(task_window.next_open_at),
        },
    )


def build_schedule_invalid_window_error(
    candidate_session,
    task,
    *,
    task_window: TaskWindow,
    coerce_task_day_index: Callable[[Any], int | None],
    serialize_optional_datetime: Callable[[datetime | None], str | None],
) -> ApiError:
    """Build schedule invalid window error."""
    return ApiError(
        status_code=status.HTTP_409_CONFLICT,
        detail="Schedule window configuration is invalid.",
        error_code=SCHEDULE_INVALID_WINDOW,
        retryable=False,
        details={
            "candidateSessionId": getattr(candidate_session, "id", None),
            "taskId": getattr(task, "id", None),
            "dayIndex": coerce_task_day_index(task),
            "windowStartAt": serialize_optional_datetime(task_window.window_start_at),
            "windowEndAt": serialize_optional_datetime(task_window.window_end_at),
        },
    )


def build_schedule_not_started_error(
    candidate_session,
    window_start_at: datetime | None,
    window_end_at: datetime | None,
    *,
    normalize_optional_datetime: Callable[[datetime | None], datetime | None],
    serialize_optional_datetime: Callable[[datetime | None], str | None],
) -> ApiError:
    """Build schedule not started error."""
    scheduled_start_at = normalize_optional_datetime(
        getattr(candidate_session, "scheduled_start_at", None)
    )
    return ApiError(
        status_code=status.HTTP_409_CONFLICT,
        detail="Simulation has not started yet.",
        error_code=SCHEDULE_NOT_STARTED,
        retryable=True,
        details={
            "startAt": serialize_optional_datetime(scheduled_start_at),
            "windowStartAt": serialize_optional_datetime(window_start_at),
            "windowEndAt": serialize_optional_datetime(window_end_at),
        },
    )


__all__ = [
    "build_schedule_invalid_window_error",
    "build_schedule_not_started_error",
    "build_task_window_closed_error",
]
