from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_schedule_gates_routes_utils import *


def test_require_active_window_raises_task_window_closed_error() -> None:
    candidate_session = _session_with_windows()
    task = _task(task_id=55, day_index=1)

    with pytest.raises(ApiError) as excinfo:
        schedule_gates.require_active_window(
            candidate_session,
            task,
            now=datetime(2026, 3, 10, 12, 0, tzinfo=UTC),
        )

    error = excinfo.value
    assert error.status_code == 409
    assert error.error_code == "TASK_WINDOW_CLOSED"
    assert error.retryable is True
    assert error.detail == "Task is closed outside the scheduled window."
    assert error.details == {
        "windowStartAt": "2026-03-10T13:00:00Z",
        "windowEndAt": "2026-03-10T21:00:00Z",
        "nextOpenAt": "2026-03-10T13:00:00Z",
    }
