from __future__ import annotations

from datetime import UTC, datetime, time

import pytest

from app.candidates.candidate_sessions.services.scheduling.candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_service import (
    coerce_utc_datetime,
    deserialize_day_windows,
    parse_local_time,
    serialize_day_windows,
)


def test_parse_local_time_and_serialization_helpers() -> None:
    assert parse_local_time("09:00") == time(hour=9, minute=0)
    assert parse_local_time(time(hour=9, minute=5, second=30)) == time(hour=9, minute=5)
    with pytest.raises(ValueError):
        parse_local_time(9)
    with pytest.raises(ValueError):
        parse_local_time("9am")
    assert coerce_utc_datetime(datetime(2026, 3, 10, 13, 0)).tzinfo == UTC

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
