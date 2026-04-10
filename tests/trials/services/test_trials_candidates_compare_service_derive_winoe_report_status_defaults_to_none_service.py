from __future__ import annotations

from tests.trials.services.trials_candidates_compare_service_utils import *


def test_derive_winoe_report_status_defaults_to_none():
    status = derive_winoe_report_status(
        has_ready_profile=False,
        latest_run_status="unknown",
        has_active_job=False,
    )
    assert status == "none"
