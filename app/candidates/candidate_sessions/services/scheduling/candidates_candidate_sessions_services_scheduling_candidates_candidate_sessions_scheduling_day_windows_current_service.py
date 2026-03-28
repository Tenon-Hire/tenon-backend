"""Application module for candidates candidate sessions services scheduling candidates candidate sessions scheduling day windows current service workflows."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any


def derive_current_day_window(
    day_windows: list[dict[str, Any]],
    *,
    coerce_utc_datetime: Callable[[datetime], datetime],
    now_utc: datetime | None = None,
) -> dict[str, Any] | None:
    """Derive current day window."""
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
