from __future__ import annotations

from tests.simulations.services.simulations_candidates_compare_service_utils import *


def test_derive_candidate_compare_status_ready_is_evaluated():
    status = derive_candidate_compare_status(
        fit_profile_status="ready",
        day_completion=_day_completion(completed_days={1, 2}),
        candidate_session_status="in_progress",
        started_at=datetime.now(UTC),
        completed_at=None,
    )
    assert status == "evaluated"
