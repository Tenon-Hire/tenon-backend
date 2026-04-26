from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_codespace_init_reuses_existing_workspace_and_skips_github(
    async_client, async_session, candidate_header_factory, override_dependencies
):
    talent_partner = await create_talent_partner(async_session, email="reuse@sim.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    # Complete day 1 to unlock day 2 code task
    await create_submission(
        async_session, candidate_session=cs, task=tasks[0], content_text="day1"
    )
    await async_session.commit()

    existing = await workspace_repo.create_workspace(
        async_session,
        candidate_session_id=cs.id,
        task_id=tasks[1].id,
        template_repo_full_name=tasks[1].template_repo or "",
        repo_full_name="org/precreated-repo",
        repo_id=321,
        default_branch="main",
        base_template_sha="base-precreated",
        created_at=datetime.now(UTC),
    )

    calls: dict[str, int] = {"create": 0}

    class CountingGithubClient:
        async def create_empty_repo(self, **_kwargs):
            calls["create"] += 1
            raise AssertionError("create_empty_repo should not be called")

        async def add_collaborator(
            self, repo_full_name: str, username: str, *, permission: str = "push"
        ):
            calls.setdefault("collab", 0)
            calls["collab"] += 1

        async def get_branch(self, repo_full_name: str, branch: str):
            return {}

        async def get_compare(self, repo_full_name: str, base: str, head: str):
            return {}

    with override_dependencies(
        {candidate_submissions.get_github_client: lambda: CountingGithubClient()}
    ):
        headers = candidate_header_factory(cs)
        resp = await async_client.post(
            f"/api/tasks/{tasks[1].id}/codespace/init",
            headers=headers,
            json={"githubUsername": "octocat"},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["workspaceId"] == existing.id
    assert body["repoFullName"] == existing.repo_full_name
    assert calls["create"] == 0

    rows = await async_session.execute(
        select(Workspace).where(
            Workspace.candidate_session_id == cs.id, Workspace.task_id == tasks[1].id
        )
    )
    assert len(list(rows.scalars())) == 1
