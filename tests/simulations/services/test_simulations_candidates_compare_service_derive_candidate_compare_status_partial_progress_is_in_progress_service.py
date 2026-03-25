from __future__ import annotations

from tests.simulations.services.simulations_candidates_compare_service_utils import *


def test_derive_candidate_compare_status_partial_progress_is_in_progress():
    status = derive_candidate_compare_status(
        fit_profile_status="none",
        day_completion=_day_completion(completed_days={1}),
        candidate_session_status="not_started",
        started_at=None,
        completed_at=None,
    )
    assert status == "in_progress"
