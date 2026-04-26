from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.candidates.candidate_sessions.repositories import (
    repository_day_audits as cs_repo,
)
from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_codespace_status_allows_before_cutoff_when_day_audit_exists(
    async_client, async_session, candidate_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="status-open-cutoff@sim.com"
    )
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
        repo_full_name="org/status-repo-open-cutoff",
        repo_id=111,
        default_branch="main",
        base_template_sha="base",
        created_at=datetime.now(UTC),
    )
    await cs_repo.create_day_audit_once(
        async_session,
        candidate_session_id=cs.id,
        day_index=tasks[1].day_index,
        cutoff_at=datetime.now(UTC) + timedelta(hours=1),
        cutoff_commit_sha="abc123def456",
        eval_basis_ref="refs/heads/main@cutoff",
        commit=True,
    )
    await async_session.commit()

    resp = await async_client.get(
        f"/api/tasks/{tasks[1].id}/codespace/status",
        headers=candidate_header_factory(cs),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["repoFullName"] == "org/status-repo-open-cutoff"
    assert data["codespaceUrl"] == (
        "https://codespaces.new/org/status-repo-open-cutoff?quickstart=1"
    )
    assert data["cutoffCommitSha"] == "abc123def456"
    assert data["cutoffAt"] is not None
    assert data["workspaceId"] == workspace.id


@pytest.mark.asyncio
async def test_codespace_init_allows_before_cutoff_when_day_audit_exists(
    async_client, async_session, candidate_header_factory, actions_stubber
):
    actions_stubber()
    talent_partner = await create_talent_partner(
        async_session, email="init-open-cutoff@sim.com"
    )
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

    await cs_repo.create_day_audit_once(
        async_session,
        candidate_session_id=cs.id,
        day_index=tasks[1].day_index,
        cutoff_at=datetime.now(UTC) + timedelta(hours=1),
        cutoff_commit_sha="cutoff-day2-sha",
        eval_basis_ref="refs/heads/main@cutoff",
        commit=True,
    )
    await async_session.commit()

    response = await async_client.post(
        f"/api/tasks/{tasks[1].id}/codespace/init",
        headers=candidate_header_factory(cs),
        json={"githubUsername": "octocat"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["repoFullName"]
    assert body["codespaceUrl"].startswith("https://codespaces.new/")
