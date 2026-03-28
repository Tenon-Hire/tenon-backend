from __future__ import annotations

from tests.simulations.services.simulations_candidates_compare_service_utils import *


def test_derive_candidate_compare_status_no_progress_is_scheduled():
    status = derive_candidate_compare_status(
        fit_profile_status="none",
        day_completion=_day_completion(),
        candidate_session_status="not_started",
        started_at=None,
        completed_at=None,
    )
    assert status == "scheduled"
