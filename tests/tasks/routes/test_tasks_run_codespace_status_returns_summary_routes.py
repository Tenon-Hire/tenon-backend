from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_codespace_status_returns_summary(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(async_session, email="status@sim.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await create_submission(
        async_session, candidate_session=cs, task=tasks[0], content_text="day1"
    )
    await async_session.commit()

    workspace = await workspace_repo.create_workspace(
        async_session,
        candidate_session_id=cs.id,
        task_id=tasks[1].id,
        template_repo_full_name=tasks[1].template_repo or "",
        repo_full_name="org/status-repo",
        repo_id=111,
        default_branch="main",
        base_template_sha="base",
        created_at=datetime.now(UTC),
    )
    workspace.last_test_summary_json = "{not-json"
    await async_session.commit()

    headers = candidate_header_factory(cs)
    resp = await async_client.get(
        f"/api/tasks/{tasks[1].id}/codespace/status",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data == {
        "repoFullName": "org/status-repo",
        "codespaceUrl": "https://codespaces.new/org/status-repo?quickstart=1",
        "codespaceState": None,
        "defaultBranch": "main",
        "latestCommitSha": None,
        "lastWorkflowRunId": None,
        "lastWorkflowConclusion": None,
        "lastTestSummary": None,
        "workspaceId": workspace.id,
        "cutoffCommitSha": None,
        "cutoffAt": None,
    }
