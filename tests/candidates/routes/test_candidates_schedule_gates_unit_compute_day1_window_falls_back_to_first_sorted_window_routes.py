from __future__ import annotations

from tests.candidates.routes.candidates_schedule_gates_routes_utils import *


def test_compute_day1_window_falls_back_to_first_sorted_window() -> None:
    candidate_session = SimpleNamespace(
        day_windows_json=[
            {
                "dayIndex": 2,
                "windowStartAt": "2026-03-11T13:00:00Z",
                "windowEndAt": "2026-03-11T21:00:00Z",
            },
            {
                "dayIndex": 3,
                "windowStartAt": "2026-03-12T13:00:00Z",
                "windowEndAt": "2026-03-12T21:00:00Z",
            },
        ],
        scheduled_start_at=None,
        trial=None,
        candidate_timezone=None,
    )

    start_at, end_at = schedule_gates.compute_day1_window(candidate_session)
    assert start_at == datetime(2026, 3, 11, 13, 0, tzinfo=UTC)
    assert end_at == datetime(2026, 3, 11, 21, 0, tzinfo=UTC)
