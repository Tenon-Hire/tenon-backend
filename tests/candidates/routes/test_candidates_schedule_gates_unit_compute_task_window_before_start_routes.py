from __future__ import annotations

from tests.candidates.routes.candidates_schedule_gates_routes_utils import *


def test_compute_task_window_before_start() -> None:
    candidate_session = _session_with_windows()
    task = _task(day_index=1)

    window = schedule_gates.compute_task_window(
        candidate_session,
        task,
        now_utc=datetime(2026, 3, 10, 12, 59, tzinfo=UTC),
    )
    assert window.is_open is False
    assert window.window_start_at == datetime(2026, 3, 10, 13, 0, tzinfo=UTC)
    assert window.window_end_at == datetime(2026, 3, 10, 21, 0, tzinfo=UTC)
    assert window.next_open_at == datetime(2026, 3, 10, 13, 0, tzinfo=UTC)
