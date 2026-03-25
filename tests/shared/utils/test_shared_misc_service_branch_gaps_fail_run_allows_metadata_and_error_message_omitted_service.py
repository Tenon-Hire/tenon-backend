from __future__ import annotations

import pytest

from tests.shared.utils.shared_misc_service_branch_gaps_utils import *


@pytest.mark.asyncio
async def test_fail_run_allows_metadata_and_error_message_omitted(monkeypatch):
    now = datetime.now(UTC).replace(microsecond=0)
    run = SimpleNamespace(
        id=88,
        candidate_session_id=9,
        scenario_version_id=7,
        status="running",
        started_at=now,
        completed_at=None,
        error_code=None,
        metadata_json={"jobId": "job-1"},
        model_name="model",
        model_version="v1",
        prompt_version="p1",
        rubric_version="r1",
        basis_fingerprint="fingerprint",
    )
    db = _DummyDB()

    async def _get_run(_db, _run_id, for_update=True):
        assert for_update is True
        return run

    monkeypatch.setattr(evaluation_runs.evaluation_repo, "get_run_by_id", _get_run)

    failed = await evaluation_runs.fail_run(
        db,
        run_id=run.id,
        completed_at=now + timedelta(seconds=1),
        commit=False,
        metadata_json=None,
        error_message=None,
    )

    assert failed is run
    assert run.status == "failed"
    assert run.metadata_json == {"jobId": "job-1"}
    assert db.flushes == 1
