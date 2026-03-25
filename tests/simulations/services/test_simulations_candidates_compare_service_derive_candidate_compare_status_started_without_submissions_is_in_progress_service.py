from __future__ import annotations

from tests.simulations.services.simulations_candidates_compare_service_utils import *


def test_derive_candidate_compare_status_started_without_submissions_is_in_progress():
    status = derive_candidate_compare_status(
        fit_profile_status="none",
        day_completion=_day_completion(),
        candidate_session_status="not_started",
        started_at=datetime.now(UTC),
        completed_at=None,
    )
    assert status == "in_progress"
