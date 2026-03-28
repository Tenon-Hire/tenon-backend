from __future__ import annotations

from tests.candidates.candidate_sessions.services.candidates_candidate_sessions_day_close_jobs_test_utils import *


def test_day_close_job_helpers_format_payload() -> None:
    key = day_close_jobs.day_close_finalize_text_idempotency_key(11, 22)
    assert key == "day_close_finalize_text:11:22"
    enforcement_key = day_close_jobs.day_close_enforcement_idempotency_key(11, 2)
    assert enforcement_key == "day_close_enforcement:11:2"

    window_end = datetime(2026, 3, 10, 18, 30, tzinfo=UTC)
    payload = day_close_jobs.build_day_close_finalize_text_payload(
        candidate_session_id=11,
        task_id=22,
        day_index=5,
        window_end_at=window_end,
    )
    assert payload == {
        "candidateSessionId": 11,
        "taskId": 22,
        "dayIndex": 5,
        "windowEndAt": "2026-03-10T18:30:00Z",
    }
    enforcement_payload = day_close_jobs.build_day_close_enforcement_payload(
        candidate_session_id=11,
        task_id=33,
        day_index=2,
        window_end_at=window_end,
    )
    assert enforcement_payload == {
        "candidateSessionId": 11,
        "taskId": 33,
        "dayIndex": 2,
        "windowEndAt": "2026-03-10T18:30:00Z",
    }
