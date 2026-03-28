from __future__ import annotations

from tests.simulations.services.simulations_candidates_compare_service_utils import *


def test_derive_fit_profile_status_failed_when_no_ready_or_active_job():
    status = derive_fit_profile_status(
        has_ready_profile=False,
        latest_run_status="failed",
        has_active_job=False,
    )
    assert status == "failed"
