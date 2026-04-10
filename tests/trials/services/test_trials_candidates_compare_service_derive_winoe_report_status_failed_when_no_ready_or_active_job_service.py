from __future__ import annotations

from tests.trials.services.trials_candidates_compare_service_utils import *


def test_derive_winoe_report_status_failed_when_no_ready_or_active_job():
    status = derive_winoe_report_status(
        has_ready_profile=False,
        latest_run_status="failed",
        has_active_job=False,
    )
    assert status == "failed"
