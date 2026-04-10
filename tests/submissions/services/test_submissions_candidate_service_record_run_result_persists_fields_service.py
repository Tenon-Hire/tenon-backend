from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_candidate_service_utils import *


@pytest.mark.asyncio
async def test_record_run_result_persists_fields(async_session):
    talent_partner = await create_talent_partner(async_session, email="record@sim.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim, status="in_progress")
    now = datetime.now(UTC)
    workspace = await workspace_repo.create_workspace(
        async_session,
        candidate_session_id=cs.id,
        task_id=tasks[1].id,
        template_repo_full_name=tasks[1].template_repo or "",
        repo_full_name="org/record-repo",
        repo_id=999,
        default_branch="main",
        base_template_sha="base",
        created_at=now,
    )

    result = ActionsRunResult(
        status="failed",
        run_id=777,
        conclusion="failure",
        passed=0,
        failed=1,
        total=1,
        stdout="boom",
        stderr=None,
        head_sha="newsha",
        html_url="https://example.com/run/777",
        raw={"summary": {"status": "failed"}},
    )

    saved = await svc.record_run_result(async_session, workspace, result)
    assert saved.last_workflow_run_id == "777"
    assert saved.last_workflow_conclusion == "failure"
    assert saved.latest_commit_sha == "newsha"
    assert saved.last_test_summary_json
