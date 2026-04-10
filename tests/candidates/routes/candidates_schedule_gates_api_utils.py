from __future__ import annotations

import json
from datetime import UTC, datetime, time, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.candidates.candidate_sessions.services.scheduling.candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_service import (
    derive_day_windows,
    serialize_day_windows,
)
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)

_START_0900 = time(hour=9)
_END_1700 = time(hour=17)


def _local_window_start_utc(timezone_name: str, *, days_ahead: int) -> datetime:
    zone = ZoneInfo(timezone_name)
    local_date = datetime.now(UTC).astimezone(zone).date() + timedelta(days=days_ahead)
    local_start = datetime.combine(local_date, time(hour=9, minute=0), tzinfo=zone)
    return local_start.astimezone(UTC).replace(microsecond=0)


async def _set_schedule(
    *,
    async_session,
    candidate_session,
    scheduled_start_at: datetime,
    timezone_name: str,
) -> list[dict[str, object]]:
    day_windows = derive_day_windows(
        scheduled_start_at_utc=scheduled_start_at,
        candidate_tz=timezone_name,
        day_window_start_local=candidate_session.trial.day_window_start_local,
        day_window_end_local=candidate_session.trial.day_window_end_local,
        overrides=candidate_session.trial.day_window_overrides_json,
        overrides_enabled=bool(candidate_session.trial.day_window_overrides_enabled),
        total_days=5,
    )
    candidate_session.scheduled_start_at = scheduled_start_at
    candidate_session.candidate_timezone = timezone_name
    candidate_session.day_windows_json = serialize_day_windows(day_windows)
    await async_session.commit()
    return day_windows


def _window_by_day(
    day_windows: list[dict[str, object]],
    *,
    day_index: int,
) -> dict[str, object]:
    for window in day_windows:
        if int(window["dayIndex"]) == day_index:
            return window
    raise AssertionError(f"Missing day window for day_index={day_index}")


def _window_iso(window: dict[str, object], key: str) -> str:
    value = window[key]
    assert isinstance(value, datetime)
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _trial(*, start: time = _START_0900, end: time = _END_1700):
    return SimpleNamespace(
        day_window_start_local=start,
        day_window_end_local=end,
        day_window_overrides_json=None,
        day_window_overrides_enabled=False,
    )


def _task(*, task_id: int = 10, day_index: int | str = 1):
    return SimpleNamespace(id=task_id, day_index=day_index)


def _session_with_windows() -> SimpleNamespace:
    return SimpleNamespace(
        id=42,
        day_windows_json=[
            {
                "dayIndex": 1,
                "windowStartAt": "2026-03-10T13:00:00Z",
                "windowEndAt": "2026-03-10T21:00:00Z",
            },
            {
                "dayIndex": 2,
                "windowStartAt": "2026-03-11T13:00:00Z",
                "windowEndAt": "2026-03-11T21:00:00Z",
            },
        ],
        scheduled_start_at=datetime(2026, 3, 10, 13, 0, tzinfo=UTC),
        trial=_trial(),
        candidate_timezone="UTC",
    )


__all__ = [name for name in globals() if not name.startswith("__")]
