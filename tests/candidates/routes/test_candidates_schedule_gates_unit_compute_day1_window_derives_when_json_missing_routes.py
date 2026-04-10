from __future__ import annotations

from tests.candidates.routes.candidates_schedule_gates_routes_utils import *


def test_compute_day1_window_derives_when_json_missing() -> None:
    scheduled_start = datetime(2026, 3, 10, 13, 0, tzinfo=UTC)
    candidate_session = SimpleNamespace(
        day_windows_json=None,
        scheduled_start_at=scheduled_start,
        trial=_trial(),
        candidate_timezone="America/New_York",
    )

    start_at, end_at = schedule_gates.compute_day1_window(candidate_session)
    assert start_at == datetime(2026, 3, 10, 13, 0, tzinfo=UTC)
    assert end_at == datetime(2026, 3, 10, 21, 0, tzinfo=UTC)
