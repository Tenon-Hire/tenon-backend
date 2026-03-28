"""Application module for candidates candidate sessions services candidates candidate sessions schedule gates loader service workflows."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, time
from typing import Any


def _load_or_derive_day_windows_impl(
    candidate_session,
    *,
    minimum_total_days: int,
    deserialize_windows: Callable[[Any], list[dict[str, Any]]],
    derive_windows: Callable[..., list[dict[str, Any]]],
    normalize_optional_datetime: Callable[[datetime | None], datetime | None],
    default_window_start: time,
    default_window_end: time,
) -> list[dict[str, Any]]:
    day_windows = deserialize_windows(
        getattr(candidate_session, "day_windows_json", None)
    )
    if day_windows:
        return sorted(day_windows, key=lambda item: int(item["dayIndex"]))
    scheduled_start_at = normalize_optional_datetime(
        getattr(candidate_session, "scheduled_start_at", None)
    )
    simulation = getattr(candidate_session, "simulation", None)
    candidate_timezone = (
        getattr(candidate_session, "candidate_timezone", None) or ""
    ).strip()
    if scheduled_start_at is None or simulation is None or not candidate_timezone:
        return []
    window_start_local = (
        getattr(simulation, "day_window_start_local", None) or default_window_start
    )
    window_end_local = (
        getattr(simulation, "day_window_end_local", None) or default_window_end
    )
    try:
        return derive_windows(
            scheduled_start_at_utc=scheduled_start_at,
            candidate_tz=candidate_timezone,
            day_window_start_local=window_start_local,
            day_window_end_local=window_end_local,
            overrides=getattr(simulation, "day_window_overrides_json", None),
            overrides_enabled=bool(
                getattr(simulation, "day_window_overrides_enabled", False)
            ),
            total_days=max(1, minimum_total_days),
        )
    except ValueError:
        return []


__all__ = ["_load_or_derive_day_windows_impl"]
