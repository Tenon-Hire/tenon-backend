"""Application module for candidates candidate sessions services scheduling candidates candidate sessions scheduling day windows utils workflows."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, time
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def coerce_utc_datetime(value: datetime) -> datetime:
    """Execute coerce utc datetime."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def validate_timezone(tz_str: str) -> str:
    """Validate timezone."""
    timezone_name = (tz_str or "").strip()
    if not timezone_name:
        raise ValueError("Timezone is required")
    try:
        return ZoneInfo(timezone_name).key
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Invalid timezone") from exc


def parse_local_time(value: Any) -> time:
    """Parse local time."""
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0)
    if not isinstance(value, str):
        raise ValueError("Time value must be HH:MM")
    try:
        parsed = datetime.strptime(value.strip(), "%H:%M")
    except ValueError as exc:
        raise ValueError("Time value must be HH:MM") from exc
    return parsed.time().replace(second=0, microsecond=0)


def _coerce_day_index(raw: Any) -> int | None:
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.strip().isdigit():
        return int(raw.strip())
    return None


def _normalize_overrides(
    overrides: Mapping[Any, Any] | None,
) -> dict[int, tuple[time, time]]:
    normalized: dict[int, tuple[time, time]] = {}
    if not isinstance(overrides, Mapping):
        return normalized
    for raw_day, raw_window in overrides.items():
        day_index = _coerce_day_index(raw_day)
        if day_index is None or not isinstance(raw_window, Mapping):
            continue
        raw_start = (
            raw_window.get("startLocal")
            or raw_window.get("windowStartLocal")
            or raw_window.get("start")
        )
        raw_end = (
            raw_window.get("endLocal")
            or raw_window.get("windowEndLocal")
            or raw_window.get("end")
        )
        if raw_start is None or raw_end is None:
            continue
        start_local = parse_local_time(raw_start)
        end_local = parse_local_time(raw_end)
        if end_local <= start_local:
            raise ValueError("Window end must be after start")
        normalized[day_index] = (start_local, end_local)
    return normalized
