"""Application module for candidates candidate sessions services scheduling candidates candidate sessions scheduling day windows derivation service workflows."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo


def derive_day_windows_impl(
    *,
    scheduled_start_at_utc: datetime,
    candidate_tz: str,
    day_window_start_local: time,
    day_window_end_local: time,
    overrides: Mapping[Any, Any] | None,
    overrides_enabled: bool,
    normalize_overrides: Callable[
        [Mapping[Any, Any] | None], dict[int, tuple[time, time]]
    ],
    validate_timezone: Callable[[str], str],
    coerce_utc_datetime: Callable[[datetime], datetime],
    total_days: int = 5,
) -> list[dict[str, Any]]:
    """Derive day windows impl."""
    if total_days <= 0:
        raise ValueError("total_days must be greater than zero")
    if day_window_end_local <= day_window_start_local:
        raise ValueError("Window end must be after start")

    zone = ZoneInfo(validate_timezone(candidate_tz))
    day_one_local_date: date = (
        coerce_utc_datetime(scheduled_start_at_utc).astimezone(zone).date()
    )
    normalized_overrides = normalize_overrides(overrides if overrides_enabled else None)
    windows: list[dict[str, Any]] = []
    for offset in range(total_days):
        day_index = offset + 1
        window_date = day_one_local_date + timedelta(days=offset)
        start_local, end_local = normalized_overrides.get(
            day_index, (day_window_start_local, day_window_end_local)
        )
        start_at = datetime.combine(window_date, start_local, tzinfo=zone).astimezone(
            UTC
        )
        end_at = datetime.combine(window_date, end_local, tzinfo=zone).astimezone(UTC)
        if end_at <= start_at:
            raise ValueError("Window end must be after start")
        windows.append(
            {"dayIndex": day_index, "windowStartAt": start_at, "windowEndAt": end_at}
        )
    return windows
