from __future__ import annotations

from tests.simulations.services.simulations_candidates_compare_service_utils import *


def test_derive_fit_profile_status_active_job_without_runs_is_generating():
    status = derive_fit_profile_status(
        has_ready_profile=False,
        latest_run_status=None,
        has_active_job=True,
    )
    assert status == "generating"
