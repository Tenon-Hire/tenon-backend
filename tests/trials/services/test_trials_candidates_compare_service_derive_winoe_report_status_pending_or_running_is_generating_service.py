from __future__ import annotations

from tests.trials.services.trials_candidates_compare_service_utils import *


def test_derive_winoe_report_status_pending_or_running_is_generating():
    pending = derive_winoe_report_status(
        has_ready_profile=False,
        latest_run_status="pending",
        has_active_job=False,
    )
    running = derive_winoe_report_status(
        has_ready_profile=False,
        latest_run_status="running",
        has_active_job=False,
    )
    assert pending == "generating"
    assert running == "generating"
