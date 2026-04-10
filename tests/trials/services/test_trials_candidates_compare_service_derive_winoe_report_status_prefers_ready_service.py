from __future__ import annotations

from tests.trials.services.trials_candidates_compare_service_utils import *


def test_derive_winoe_report_status_prefers_ready():
    status = derive_winoe_report_status(
        has_ready_profile=True,
        latest_run_status="failed",
        has_active_job=True,
    )
    assert status == "ready"
