from __future__ import annotations

from datetime import UTC, datetime, time

from app.candidates.candidate_sessions.services.scheduling.candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_service import (
    derive_current_day_window,
    derive_day_windows,
)


def test_derive_day_windows_new_york_defaults() -> None:
    windows = derive_day_windows(
        scheduled_start_at_utc=datetime(2026, 3, 10, 13, 0, tzinfo=UTC),
        candidate_tz="America/New_York",
        day_window_start_local=time(hour=9, minute=0),
        day_window_end_local=time(hour=17, minute=0),
        overrides=None,
        overrides_enabled=False,
        total_days=5,
    )
    assert len(windows) == 5
    assert windows[0]["dayIndex"] == 1
    assert windows[0]["windowStartAt"] == datetime(2026, 3, 10, 13, 0, tzinfo=UTC)
    assert windows[0]["windowEndAt"] == datetime(2026, 3, 10, 21, 0, tzinfo=UTC)
    assert windows[-1]["dayIndex"] == 5


def test_derive_day_windows_handles_dst_transition() -> None:
    windows = derive_day_windows(
        scheduled_start_at_utc=datetime(2026, 3, 7, 14, 0, tzinfo=UTC),
        candidate_tz="America/New_York",
        day_window_start_local=time(hour=9, minute=0),
        day_window_end_local=time(hour=17, minute=0),
        overrides=None,
        overrides_enabled=False,
        total_days=3,
    )
    assert windows[0]["windowStartAt"] == datetime(2026, 3, 7, 14, 0, tzinfo=UTC)
    assert windows[0]["windowEndAt"] == datetime(2026, 3, 7, 22, 0, tzinfo=UTC)
    assert windows[1]["windowStartAt"] == datetime(2026, 3, 8, 13, 0, tzinfo=UTC)
    assert windows[1]["windowEndAt"] == datetime(2026, 3, 8, 21, 0, tzinfo=UTC)


def test_derive_current_day_window_states() -> None:
    windows = derive_day_windows(
        scheduled_start_at_utc=datetime(2026, 3, 10, 13, 0, tzinfo=UTC),
        candidate_tz="America/New_York",
        day_window_start_local=time(hour=9, minute=0),
        day_window_end_local=time(hour=17, minute=0),
        overrides=None,
        overrides_enabled=False,
        total_days=2,
    )
    upcoming = derive_current_day_window(
        windows, now_utc=datetime(2026, 3, 10, 12, 59, tzinfo=UTC)
    )
    assert upcoming is not None
    assert upcoming["state"] == "upcoming"
    assert upcoming["dayIndex"] == 1

    active = derive_current_day_window(
        windows, now_utc=datetime(2026, 3, 10, 13, 30, tzinfo=UTC)
    )
    assert active is not None
    assert active["state"] == "active"
    assert active["dayIndex"] == 1

    closed = derive_current_day_window(
        windows, now_utc=datetime(2026, 3, 12, 0, 0, tzinfo=UTC)
    )
    assert closed is not None
    assert closed["state"] == "closed"
    assert closed["dayIndex"] == 2
