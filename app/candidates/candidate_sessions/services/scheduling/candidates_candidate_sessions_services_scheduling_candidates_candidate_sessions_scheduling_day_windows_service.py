"""Application module for candidates candidate sessions services scheduling candidates candidate sessions scheduling day windows service workflows."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, time
from typing import Any, Literal

from .candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_current_service import (
    derive_current_day_window as _derive_current_day_window,
)
from .candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_derivation_service import (
    derive_day_windows_impl,
)
from .candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_serialization_service import (
    deserialize_day_windows as _deserialize_day_windows,
)
from .candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_serialization_service import (
    serialize_day_windows as _serialize_day_windows,
)
from .candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_utils import (
    _coerce_day_index,
    _normalize_overrides,
    coerce_utc_datetime,
    parse_local_time,
    validate_timezone,
)

ScheduleWindowState = Literal["upcoming", "active", "closed"]


def serialize_day_windows(day_windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Serialize day windows."""
    return _serialize_day_windows(day_windows, coerce_utc_datetime=coerce_utc_datetime)


def deserialize_day_windows(raw_value: Any) -> list[dict[str, Any]]:
    """Execute deserialize day windows."""
    return _deserialize_day_windows(
        raw_value,
        coerce_day_index=_coerce_day_index,
        coerce_utc_datetime=coerce_utc_datetime,
    )


def derive_day_windows(
    *,
    scheduled_start_at_utc: datetime,
    candidate_tz: str,
    day_window_start_local: time,
    day_window_end_local: time,
    overrides: Mapping[Any, Any] | None,
    overrides_enabled: bool,
    total_days: int = 5,
) -> list[dict[str, Any]]:
    """Derive day windows."""
    return derive_day_windows_impl(
        scheduled_start_at_utc=scheduled_start_at_utc,
        candidate_tz=candidate_tz,
        day_window_start_local=day_window_start_local,
        day_window_end_local=day_window_end_local,
        overrides=overrides,
        overrides_enabled=overrides_enabled,
        normalize_overrides=_normalize_overrides,
        validate_timezone=validate_timezone,
        coerce_utc_datetime=coerce_utc_datetime,
        total_days=total_days,
    )


def derive_current_day_window(
    day_windows: list[dict[str, Any]],
    *,
    now_utc: datetime | None = None,
) -> dict[str, Any] | None:
    """Derive current day window."""
    return _derive_current_day_window(
        day_windows,
        coerce_utc_datetime=coerce_utc_datetime,
        now_utc=now_utc,
    )


__all__ = [
    "ScheduleWindowState",
    "coerce_utc_datetime",
    "validate_timezone",
    "parse_local_time",
    "serialize_day_windows",
    "deserialize_day_windows",
    "derive_day_windows",
    "derive_current_day_window",
]
