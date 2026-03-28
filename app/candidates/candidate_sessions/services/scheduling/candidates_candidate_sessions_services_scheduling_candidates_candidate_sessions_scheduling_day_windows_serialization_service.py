"""Application module for candidates candidate sessions services scheduling candidates candidate sessions scheduling day windows serialization service workflows."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any


def _format_utc_iso(
    value: datetime, *, coerce_utc_datetime: Callable[[datetime], datetime]
) -> str:
    canonical = coerce_utc_datetime(value).replace(microsecond=0)
    return canonical.isoformat(timespec="seconds").replace("+00:00", "Z")


def serialize_day_windows(
    day_windows: list[dict[str, Any]],
    *,
    coerce_utc_datetime: Callable[[datetime], datetime],
) -> list[dict[str, Any]]:
    """Serialize day windows."""
    return [
        {
            "dayIndex": int(window["dayIndex"]),
            "windowStartAt": _format_utc_iso(
                window["windowStartAt"], coerce_utc_datetime=coerce_utc_datetime
            ),
            "windowEndAt": _format_utc_iso(
                window["windowEndAt"], coerce_utc_datetime=coerce_utc_datetime
            ),
        }
        for window in day_windows
    ]


def deserialize_day_windows(
    raw_value: Any,
    *,
    coerce_day_index: Callable[[Any], int | None],
    coerce_utc_datetime: Callable[[datetime], datetime],
) -> list[dict[str, Any]]:
    """Execute deserialize day windows."""
    if not isinstance(raw_value, list):
        return []

    windows: list[dict[str, Any]] = []
    for item in raw_value:
        if not isinstance(item, Mapping):
            continue
        day_index = coerce_day_index(item.get("dayIndex"))
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
            {"dayIndex": day_index, "windowStartAt": start_dt, "windowEndAt": end_dt}
        )

    windows.sort(key=lambda item: int(item["dayIndex"]))
    return windows
