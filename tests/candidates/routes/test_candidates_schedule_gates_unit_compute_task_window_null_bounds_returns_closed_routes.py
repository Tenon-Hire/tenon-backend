from __future__ import annotations

from tests.candidates.routes.candidates_schedule_gates_routes_utils import *


def test_compute_task_window_null_bounds_returns_closed(monkeypatch) -> None:
    candidate_session = _session_with_windows()
    task = _task(day_index=1)
    monkeypatch.setattr(
        schedule_gates,
        "_load_or_derive_day_windows",
        lambda *_a, **_k: [{"dayIndex": 1, "windowStartAt": None, "windowEndAt": None}],
    )

    window = schedule_gates.compute_task_window(
        candidate_session,
        task,
        now_utc=datetime(2026, 3, 10, 16, 0, tzinfo=UTC),
    )
    assert window.is_open is False
    assert window.window_start_at is None
    assert window.window_end_at is None
