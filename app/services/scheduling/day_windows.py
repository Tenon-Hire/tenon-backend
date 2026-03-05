from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ScheduleWindowState = Literal["upcoming", "active", "closed"]


def coerce_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def validate_timezone(tz_str: str) -> str:
    timezone_name = (tz_str or "").strip()
    if not timezone_name:
        raise ValueError("Timezone is required")
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Invalid timezone") from exc
    return zone.key


def parse_local_time(value: Any) -> time:
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0)
    if not isinstance(value, str):
        raise ValueError("Time value must be HH:MM")
    raw = value.strip()
    try:
        parsed = datetime.strptime(raw, "%H:%M")
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
        if day_index is None:
            continue
        if not isinstance(raw_window, Mapping):
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


def _format_utc_iso(value: datetime) -> str:
    canonical = coerce_utc_datetime(value).replace(microsecond=0)
    return canonical.isoformat(timespec="seconds").replace("+00:00", "Z")


def serialize_day_windows(
    day_windows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for window in day_windows:
        payload.append(
            {
                "dayIndex": int(window["dayIndex"]),
                "windowStartAt": _format_utc_iso(window["windowStartAt"]),
                "windowEndAt": _format_utc_iso(window["windowEndAt"]),
            }
        )
    return payload


def deserialize_day_windows(raw_value: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_value, list):
        return []

    windows: list[dict[str, Any]] = []
    for item in raw_value:
        if not isinstance(item, Mapping):
            continue
        day_index = _coerce_day_index(item.get("dayIndex"))
        start_raw = item.get("windowStartAt")
        end_raw = item.get("windowEndAt")
        if (
            day_index is None
            or not isinstance(start_raw, str)
            or not isinstance(end_raw, str)
        ):
            continue
        try:
            start_dt = coerce_utc_datetime(
                datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
            )
            end_dt = coerce_utc_datetime(
                datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
            )
        except ValueError:
            continue
        windows.append(
            {
                "dayIndex": day_index,
                "windowStartAt": start_dt,
                "windowEndAt": end_dt,
            }
        )

    windows.sort(key=lambda item: int(item["dayIndex"]))
    return windows


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
    if total_days <= 0:
        raise ValueError("total_days must be greater than zero")
    if day_window_end_local <= day_window_start_local:
        raise ValueError("Window end must be after start")

    timezone_name = validate_timezone(candidate_tz)
    zone = ZoneInfo(timezone_name)
    scheduled_start = coerce_utc_datetime(scheduled_start_at_utc)
    day_one_local_date: date = scheduled_start.astimezone(zone).date()
    normalized_overrides = _normalize_overrides(
        overrides if overrides_enabled else None
    )

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
            {
                "dayIndex": day_index,
                "windowStartAt": start_at,
                "windowEndAt": end_at,
            }
        )
    return windows


def derive_current_day_window(
    day_windows: list[dict[str, Any]],
    *,
    now_utc: datetime | None = None,
) -> dict[str, Any] | None:
    if not day_windows:
        return None

    now = coerce_utc_datetime(now_utc or datetime.now(UTC))
    ordered = sorted(day_windows, key=lambda item: int(item["dayIndex"]))

    for window in ordered:
        start_at = coerce_utc_datetime(window["windowStartAt"])
        end_at = coerce_utc_datetime(window["windowEndAt"])
        if start_at <= now < end_at:
            return {
                "dayIndex": int(window["dayIndex"]),
                "windowStartAt": start_at,
                "windowEndAt": end_at,
                "state": "active",
            }
        if now < start_at:
            return {
                "dayIndex": int(window["dayIndex"]),
                "windowStartAt": start_at,
                "windowEndAt": end_at,
                "state": "upcoming",
            }

    last_window = ordered[-1]
    return {
        "dayIndex": int(last_window["dayIndex"]),
        "windowStartAt": coerce_utc_datetime(last_window["windowStartAt"]),
        "windowEndAt": coerce_utc_datetime(last_window["windowEndAt"]),
        "state": "closed",
    }


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
