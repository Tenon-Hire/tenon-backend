from __future__ import annotations

from tests.candidates.routes.candidates_schedule_gates_routes_utils import *


def test_compute_task_window_derives_with_real_timezone_dst_safe() -> None:
    candidate_session = SimpleNamespace(
        day_windows_json=None,
        scheduled_start_at=datetime(2026, 3, 8, 13, 0, tzinfo=UTC),
        trial=_trial(),
        candidate_timezone="America/New_York",
    )
    task = _task(day_index=1)

    window = schedule_gates.compute_task_window(
        candidate_session,
        task,
        now_utc=datetime(2026, 3, 8, 13, 0, tzinfo=UTC),
    )
    assert window.window_start_at == datetime(2026, 3, 8, 13, 0, tzinfo=UTC)
    assert window.window_end_at == datetime(2026, 3, 8, 21, 0, tzinfo=UTC)
    assert window.is_open is True
