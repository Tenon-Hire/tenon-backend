from __future__ import annotations

from datetime import UTC, datetime, time
from types import SimpleNamespace

from app.candidates.candidate_sessions.services import schedule_gates
from app.shared.utils.shared_utils_errors_utils import ApiError

_START_0900 = time(hour=9)

_END_1700 = time(hour=17)


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
