from __future__ import annotations

from datetime import UTC, datetime, time

import pytest

import app.services.scheduling.day_windows as day_windows_module
from app.services.scheduling.day_windows import (
    coerce_utc_datetime,
    derive_current_day_window,
    derive_day_windows,
    deserialize_day_windows,
    parse_local_time,
    serialize_day_windows,
    validate_timezone,
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


def test_validate_timezone_rejects_invalid_value() -> None:
    with pytest.raises(ValueError):
        validate_timezone("Mars/Olympus_Mons")

    with pytest.raises(ValueError):
        validate_timezone("   ")


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
    # DST starts in New York on 2026-03-08, shifting 09:00 local to 13:00 UTC.
    assert windows[1]["windowStartAt"] == datetime(2026, 3, 8, 13, 0, tzinfo=UTC)
    assert windows[1]["windowEndAt"] == datetime(2026, 3, 8, 21, 0, tzinfo=UTC)


def test_parse_local_time_and_serialization_helpers() -> None:
    assert parse_local_time("09:00") == time(hour=9, minute=0)
    assert parse_local_time(time(hour=9, minute=5, second=30)) == time(hour=9, minute=5)
    with pytest.raises(ValueError):
        parse_local_time(9)
    with pytest.raises(ValueError):
        parse_local_time("9am")

    naive = datetime(2026, 3, 10, 13, 0)
    assert coerce_utc_datetime(naive).tzinfo == UTC

    windows = [
        {
            "dayIndex": 1,
            "windowStartAt": datetime(2026, 3, 10, 13, 0, 0, 123456, tzinfo=UTC),
            "windowEndAt": datetime(2026, 3, 10, 21, 0, 0, 654321, tzinfo=UTC),
        }
    ]
    serialized = serialize_day_windows(windows)
    assert serialized == [
        {
            "dayIndex": 1,
            "windowStartAt": "2026-03-10T13:00:00Z",
            "windowEndAt": "2026-03-10T21:00:00Z",
        }
    ]
    assert deserialize_day_windows(serialized) == [
        {
            "dayIndex": 1,
            "windowStartAt": datetime(2026, 3, 10, 13, 0, tzinfo=UTC),
            "windowEndAt": datetime(2026, 3, 10, 21, 0, tzinfo=UTC),
        }
    ]

    # Invalid payload entries should be ignored, not crash.
    assert deserialize_day_windows("bad") == []
    assert (
        deserialize_day_windows(
            [
                123,
                {"bad": "entry"},
                {
                    "dayIndex": "x",
                    "windowStartAt": "2026-03-10T13:00:00Z",
                    "windowEndAt": "2026-03-10T21:00:00Z",
                },
                {
                    "dayIndex": 1,
                    "windowStartAt": "not-a-date",
                    "windowEndAt": "2026-03-10T21:00:00Z",
                },
            ]
        )
        == []
    )


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
        windows,
        now_utc=datetime(2026, 3, 10, 12, 59, tzinfo=UTC),
    )
    assert upcoming is not None
    assert upcoming["state"] == "upcoming"
    assert upcoming["dayIndex"] == 1

    active = derive_current_day_window(
        windows,
        now_utc=datetime(2026, 3, 10, 13, 30, tzinfo=UTC),
    )
    assert active is not None
    assert active["state"] == "active"
    assert active["dayIndex"] == 1

    closed = derive_current_day_window(
        windows,
        now_utc=datetime(2026, 3, 12, 0, 0, tzinfo=UTC),
    )
    assert closed is not None
    assert closed["state"] == "closed"
    assert closed["dayIndex"] == 2
