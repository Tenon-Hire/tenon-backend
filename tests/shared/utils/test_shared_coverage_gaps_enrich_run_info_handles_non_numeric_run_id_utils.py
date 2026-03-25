from __future__ import annotations

from tests.shared.utils.shared_coverage_gaps_utils import *


def test_enrich_run_info_handles_non_numeric_run_id():
    sub = SimpleNamespace(
        workflow_run_id="not-a-number",
        workflow_run_status="queued",
        workflow_run_conclusion="timed_out",
        commit_sha="abc",
        last_run_at=datetime.now(UTC),
    )
    run_id, conclusion, timeout, *_ = enrich_run_info(sub, None, None, None)
    assert run_id == "not-a-number"
    assert conclusion == "timed_out"
    assert timeout is True
