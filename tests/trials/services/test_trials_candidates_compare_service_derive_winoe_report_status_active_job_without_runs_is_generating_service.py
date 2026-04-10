from __future__ import annotations

from tests.trials.services.trials_candidates_compare_service_utils import *


def test_derive_winoe_report_status_active_job_without_runs_is_generating():
    status = derive_winoe_report_status(
        has_ready_profile=False,
        latest_run_status=None,
        has_active_job=True,
    )
    assert status == "generating"
