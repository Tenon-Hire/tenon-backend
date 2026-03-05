from __future__ import annotations

from datetime import UTC, datetime, time
from types import SimpleNamespace

from app.services.candidate_sessions import schedule_gates

_START_0900 = time(hour=9)
_END_1700 = time(hour=17)


def _simulation(*, start: time = _START_0900, end: time = _END_1700):
    return SimpleNamespace(
        day_window_start_local=start,
        day_window_end_local=end,
        day_window_overrides_json=None,
        day_window_overrides_enabled=False,
    )


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
        simulation=None,
        candidate_timezone=None,
    )

    start_at, end_at = schedule_gates.compute_day1_window(candidate_session)
    assert start_at == datetime(2026, 3, 11, 13, 0, tzinfo=UTC)
    assert end_at == datetime(2026, 3, 11, 21, 0, tzinfo=UTC)


def test_compute_day1_window_derives_when_json_missing() -> None:
    scheduled_start = datetime(2026, 3, 10, 13, 0, tzinfo=UTC)
    candidate_session = SimpleNamespace(
        day_windows_json=None,
        scheduled_start_at=scheduled_start,
        simulation=_simulation(),
        candidate_timezone="America/New_York",
    )

    start_at, end_at = schedule_gates.compute_day1_window(candidate_session)
    assert start_at == datetime(2026, 3, 10, 13, 0, tzinfo=UTC)
    assert end_at == datetime(2026, 3, 10, 21, 0, tzinfo=UTC)


def test_compute_day1_window_handles_invalid_window_config() -> None:
    scheduled_start = datetime(2026, 3, 10, 13, 0, tzinfo=UTC)
    candidate_session = SimpleNamespace(
        day_windows_json=None,
        scheduled_start_at=scheduled_start,
        simulation=_simulation(start=time(hour=17), end=time(hour=9)),
        candidate_timezone="America/New_York",
    )

    start_at, end_at = schedule_gates.compute_day1_window(candidate_session)
    assert start_at == scheduled_start
    assert end_at is None


def test_compute_day1_window_handles_empty_derived_windows(monkeypatch) -> None:
    scheduled_start = datetime(2026, 3, 10, 13, 0, tzinfo=UTC)
    candidate_session = SimpleNamespace(
        day_windows_json=None,
        scheduled_start_at=scheduled_start,
        simulation=_simulation(),
        candidate_timezone="America/New_York",
    )
    monkeypatch.setattr(schedule_gates, "derive_day_windows", lambda **_kwargs: [])

    start_at, end_at = schedule_gates.compute_day1_window(candidate_session)
    assert start_at == scheduled_start
    assert end_at is None


def test_build_schedule_not_started_error_allows_null_detail_fields() -> None:
    candidate_session = SimpleNamespace(
        id=1,
        scheduled_start_at=None,
    )

    error = schedule_gates.build_schedule_not_started_error(
        candidate_session, None, None
    )
    assert error.error_code == "SCHEDULE_NOT_STARTED"
    assert error.details == {
        "startAt": None,
        "windowStartAt": None,
        "windowEndAt": None,
    }
