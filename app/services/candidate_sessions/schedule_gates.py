from __future__ import annotations

import logging
from datetime import UTC, datetime, time
from typing import Any

from fastapi import status

from app.core.errors import SCHEDULE_NOT_STARTED, ApiError
from app.services.scheduling.day_windows import (
    coerce_utc_datetime,
    derive_day_windows,
    deserialize_day_windows,
)

logger = logging.getLogger(__name__)

_DEFAULT_WINDOW_START = time(hour=9, minute=0)
_DEFAULT_WINDOW_END = time(hour=17, minute=0)


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


def compute_day1_window(candidate_session) -> tuple[datetime | None, datetime | None]:
    day_windows = deserialize_day_windows(
        getattr(candidate_session, "day_windows_json", None)
    )
    day1_window = _pick_day1_window(day_windows)
    if day1_window is not None:
        return (
            _normalize_optional_datetime(day1_window["windowStartAt"]),
            _normalize_optional_datetime(day1_window["windowEndAt"]),
        )

    scheduled_start_at = _normalize_optional_datetime(
        getattr(candidate_session, "scheduled_start_at", None)
    )
    simulation = getattr(candidate_session, "simulation", None)
    candidate_timezone = (
        getattr(candidate_session, "candidate_timezone", None) or ""
    ).strip()
    if scheduled_start_at is None or simulation is None or not candidate_timezone:
        return scheduled_start_at, None

    window_start_local = (
        getattr(simulation, "day_window_start_local", None) or _DEFAULT_WINDOW_START
    )
    window_end_local = (
        getattr(simulation, "day_window_end_local", None) or _DEFAULT_WINDOW_END
    )
    try:
        derived = derive_day_windows(
            scheduled_start_at_utc=scheduled_start_at,
            candidate_tz=candidate_timezone,
            day_window_start_local=window_start_local,
            day_window_end_local=window_end_local,
            overrides=getattr(simulation, "day_window_overrides_json", None),
            overrides_enabled=bool(
                getattr(simulation, "day_window_overrides_enabled", False)
            ),
            total_days=1,
        )
    except ValueError:
        return scheduled_start_at, None

    if not derived:
        return scheduled_start_at, None
    day1 = derived[0]
    return (
        _normalize_optional_datetime(day1["windowStartAt"]),
        _normalize_optional_datetime(day1["windowEndAt"]),
    )


def build_schedule_not_started_error(
    candidate_session,
    window_start_at: datetime | None,
    window_end_at: datetime | None,
) -> ApiError:
    scheduled_start_at = _normalize_optional_datetime(
        getattr(candidate_session, "scheduled_start_at", None)
    )
    return ApiError(
        status_code=status.HTTP_409_CONFLICT,
        detail="Simulation has not started yet.",
        error_code=SCHEDULE_NOT_STARTED,
        retryable=True,
        details={
            "startAt": _serialize_optional_datetime(scheduled_start_at),
            "windowStartAt": _serialize_optional_datetime(window_start_at),
            "windowEndAt": _serialize_optional_datetime(window_end_at),
        },
    )


def is_schedule_started_for_content(
    candidate_session,
    *,
    now: datetime | None = None,
) -> bool:
    resolved_now = coerce_utc_datetime(now or datetime.now(UTC))
    window_start_at, _ = compute_day1_window(candidate_session)
    if window_start_at is None:
        return False
    return resolved_now >= window_start_at


def ensure_schedule_started_for_content(
    candidate_session,
    *,
    now: datetime | None = None,
) -> None:
    resolved_now = coerce_utc_datetime(now or datetime.now(UTC))
    window_start_at, window_end_at = compute_day1_window(candidate_session)
    if is_schedule_started_for_content(candidate_session, now=resolved_now):
        return

    scheduled_start_at = _normalize_optional_datetime(
        getattr(candidate_session, "scheduled_start_at", None)
    )
    logger.info(
        "Candidate schedule gate blocked candidateSessionId=%s scheduledStartAt=%s",
        getattr(candidate_session, "id", None),
        _serialize_optional_datetime(scheduled_start_at),
    )
    raise build_schedule_not_started_error(
        candidate_session, window_start_at, window_end_at
    )


__all__ = [
    "compute_day1_window",
    "build_schedule_not_started_error",
    "is_schedule_started_for_content",
    "ensure_schedule_started_for_content",
]
