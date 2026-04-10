from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_codespace_status_includes_cutoff_fields_when_day_audit_exists(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="status-cutoff-fields@sim.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    day2_task = tasks[1]
    await create_submission(
        async_session, candidate_session=cs, task=tasks[0], content_text="day1"
    )
    await async_session.commit()

    await workspace_repo.create_workspace(
        async_session,
        candidate_session_id=cs.id,
        task_id=day2_task.id,
        template_repo_full_name=day2_task.template_repo or "",
        repo_full_name="org/status-repo-with-cutoff",
        repo_id=112,
        default_branch="main",
        base_template_sha="base",
        precommit_sha="precommit-sha-xyz",
        created_at=datetime.now(UTC),
    )
    cutoff_at = datetime(2026, 3, 8, 17, 45, tzinfo=UTC)
    await cs_repo.create_day_audit_once(
        async_session,
        candidate_session_id=cs.id,
        day_index=day2_task.day_index,
        cutoff_at=cutoff_at,
        cutoff_commit_sha="abc123def456",
        eval_basis_ref="refs/heads/main@cutoff",
        commit=True,
    )
    await async_session.commit()

    headers = candidate_header_factory(cs)
    resp = await async_client.get(
        f"/api/tasks/{day2_task.id}/codespace/status",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["repoFullName"] == "org/status-repo-with-cutoff"
    assert data["baseTemplateSha"] == "base"
    assert data["precommitSha"] == "precommit-sha-xyz"
    assert data["cutoffCommitSha"] == "abc123def456"
    assert data["cutoffAt"] == "2026-03-08T17:45:00Z"
