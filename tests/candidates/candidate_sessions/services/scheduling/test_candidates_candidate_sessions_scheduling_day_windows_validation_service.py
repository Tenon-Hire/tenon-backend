from __future__ import annotations

from datetime import UTC, datetime, time

import pytest

import app.candidates.candidate_sessions.services.scheduling.candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_service as day_windows_module
from app.candidates.candidate_sessions.services.scheduling.candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_service import (
    derive_day_windows,
    validate_timezone,
)


def test_validate_timezone_rejects_invalid_value() -> None:
    with pytest.raises(ValueError):
        validate_timezone("Mars/Olympus_Mons")
    with pytest.raises(ValueError):
        validate_timezone("   ")


def test_derive_day_windows_validates_bounds_and_overrides() -> None:
    with pytest.raises(ValueError):
        derive_day_windows(
            scheduled_start_at_utc=datetime(2026, 3, 10, 13, 0, tzinfo=UTC),
            candidate_tz="America/New_York",
            day_window_start_local=time(hour=9, minute=0),
            day_window_end_local=time(hour=17, minute=0),
            overrides=None,
            overrides_enabled=False,
            total_days=0,
        )
    with pytest.raises(ValueError):
        derive_day_windows(
            scheduled_start_at_utc=datetime(2026, 3, 10, 13, 0, tzinfo=UTC),
            candidate_tz="America/New_York",
            day_window_start_local=time(hour=17, minute=0),
            day_window_end_local=time(hour=9, minute=0),
            overrides=None,
            overrides_enabled=False,
            total_days=5,
        )
    with pytest.raises(ValueError):
        derive_day_windows(
            scheduled_start_at_utc=datetime(2026, 3, 10, 13, 0, tzinfo=UTC),
            candidate_tz="America/New_York",
            day_window_start_local=time(hour=9, minute=0),
            day_window_end_local=time(hour=17, minute=0),
            overrides={"1": {"startLocal": "10:00", "endLocal": "09:00"}},
            overrides_enabled=True,
            total_days=5,
        )
    windows = derive_day_windows(
        scheduled_start_at_utc=datetime(2026, 3, 10, 13, 0, tzinfo=UTC),
        candidate_tz="America/New_York",
        day_window_start_local=time(hour=9, minute=0),
        day_window_end_local=time(hour=17, minute=0),
        overrides={
            "1": {"startLocal": "10:00", "endLocal": "18:00"},
            "x": {"startLocal": "11:00", "endLocal": "12:00"},
            "2": {"start": "07:00", "end": "08:00"},
            "3": {"windowStartLocal": "12:00", "windowEndLocal": "19:00"},
            "4": "not-a-map",
            "5": {"startLocal": "13:00"},
        },
        overrides_enabled=True,
        total_days=5,
    )
    assert windows[0]["windowStartAt"] == datetime(2026, 3, 10, 14, 0, tzinfo=UTC)
    assert windows[0]["windowEndAt"] == datetime(2026, 3, 10, 22, 0, tzinfo=UTC)
    assert windows[1]["windowStartAt"] == datetime(2026, 3, 11, 11, 0, tzinfo=UTC)
    assert windows[1]["windowEndAt"] == datetime(2026, 3, 11, 12, 0, tzinfo=UTC)
    assert windows[2]["windowStartAt"] == datetime(2026, 3, 12, 16, 0, tzinfo=UTC)
    assert windows[2]["windowEndAt"] == datetime(2026, 3, 12, 23, 0, tzinfo=UTC)


def test_derive_day_windows_rejects_non_monotonic_utc_override_window(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        day_windows_module,
        "_normalize_overrides",
        lambda _overrides: {1: (time(hour=18, minute=0), time(hour=9, minute=0))},
    )
    with pytest.raises(ValueError):
        derive_day_windows(
            scheduled_start_at_utc=datetime(2026, 3, 10, 13, 0, tzinfo=UTC),
            candidate_tz="America/New_York",
            day_window_start_local=time(hour=9, minute=0),
            day_window_end_local=time(hour=17, minute=0),
            overrides={"1": {"startLocal": "18:00", "endLocal": "09:00"}},
            overrides_enabled=True,
            total_days=1,
        )
