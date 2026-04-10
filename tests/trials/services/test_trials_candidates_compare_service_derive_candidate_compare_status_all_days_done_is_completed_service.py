from __future__ import annotations

from tests.trials.services.trials_candidates_compare_service_utils import *


def test_derive_candidate_compare_status_all_days_done_is_completed():
    status = derive_candidate_compare_status(
        winoe_report_status="none",
        day_completion=_day_completion(completed_days={1, 2, 3, 4, 5}),
        candidate_session_status="in_progress",
        started_at=datetime.now(UTC),
        completed_at=None,
    )
    assert status == "completed"
