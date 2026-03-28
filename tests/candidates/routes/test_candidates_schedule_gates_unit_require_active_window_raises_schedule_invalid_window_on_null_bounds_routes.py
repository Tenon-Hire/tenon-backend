from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_schedule_gates_routes_utils import *


def test_require_active_window_raises_schedule_invalid_window_on_null_bounds(
    monkeypatch,
) -> None:
    candidate_session = _session_with_windows()
    task = _task(task_id=55, day_index=1)
    monkeypatch.setattr(
        schedule_gates,
        "_load_or_derive_day_windows",
        lambda *_a, **_k: [{"dayIndex": 1, "windowStartAt": None, "windowEndAt": None}],
    )

    with pytest.raises(ApiError) as excinfo:
        schedule_gates.require_active_window(
            candidate_session,
            task,
            now=datetime(2026, 3, 10, 12, 0, tzinfo=UTC),
        )

    error = excinfo.value
    assert error.status_code == 409
    assert error.error_code == "SCHEDULE_INVALID_WINDOW"
    assert error.retryable is False
    assert error.detail == "Schedule window configuration is invalid."
    assert error.details == {
        "candidateSessionId": 42,
        "taskId": 55,
        "dayIndex": 1,
        "windowStartAt": None,
        "windowEndAt": None,
    }
