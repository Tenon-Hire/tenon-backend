from __future__ import annotations

from tests.simulations.services.simulations_candidates_compare_service_utils import *


def test_derive_fit_profile_status_prefers_ready():
    status = derive_fit_profile_status(
        has_ready_profile=True,
        latest_run_status="failed",
        has_active_job=True,
    )
    assert status == "ready"
