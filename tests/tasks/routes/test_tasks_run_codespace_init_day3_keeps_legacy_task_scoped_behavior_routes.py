from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_codespace_init_day3_keeps_legacy_task_scoped_behavior(
    async_client, async_session, candidate_header_factory, override_dependencies
):
    talent_partner = await create_talent_partner(
        async_session, email="legacy-task-scope@sim.com"
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
    await create_submission(
        async_session, candidate_session=cs, task=tasks[1], content_text="day2"
    )
    await async_session.commit()

    legacy_day2 = await workspace_repo.create_workspace(
        async_session,
        candidate_session_id=cs.id,
        task_id=tasks[1].id,
        template_repo_full_name=tasks[1].template_repo or "",
        repo_full_name="org/legacy-day2-repo",
        repo_id=321,
        default_branch="main",
        base_template_sha="base-precreated",
        created_at=datetime.now(UTC),
    )

    calls: dict[str, int] = {"create": 0}

    class StubGithubClient:
        async def create_empty_repo(
            self, *, owner, repo_name, private=True, default_branch="main"
        ):
            calls["create"] += 1
            return {
                "owner": {"login": owner},
                "name": repo_name,
                "full_name": f"{owner}/{repo_name}",
                "id": 900 + calls["create"],
                "default_branch": default_branch,
            }

        async def get_file_contents(self, *_a, **_k):
            raise GithubError("missing", status_code=404)

        async def add_collaborator(
            self, repo_full_name: str, username: str, *, permission: str = "push"
        ):
            return {"ok": True}

        async def get_branch(self, repo_full_name: str, branch: str):
            raise GithubError("missing", status_code=404)

        async def create_or_update_file(self, *_a, **_k):
            return {"content": {"sha": "readme-sha"}}

        async def create_blob(self, *_a, **_k):
            return {"sha": "blob-sha"}

        async def create_tree(self, *_a, **_k):
            return {"sha": "tree-sha"}

        async def create_commit(self, *_a, **_k):
            return {"sha": "commit-sha"}

        async def create_ref(self, *_a, **_k):
            return {"ref": "refs/heads/main", "sha": "commit-sha"}

        async def create_codespace(self, *_a, **_k):
            return {
                "name": "codespace-day3",
                "state": "available",
                "web_url": "https://codespace.example",
            }

        async def get_authenticated_user_login(self):
            return "octocat"

    with override_dependencies(
        {candidate_submissions.get_github_client: lambda: StubGithubClient()}
    ):
        headers = candidate_header_factory(cs)
        day3_init = await async_client.post(
            f"/api/tasks/{tasks[2].id}/codespace/init",
            headers=headers,
            json={"githubUsername": "octocat"},
        )
        assert day3_init.status_code == 200, day3_init.text
        day3_repo = day3_init.json()["repoFullName"]

        day2_status = await async_client.get(
            f"/api/tasks/{tasks[1].id}/codespace/status",
            headers=headers,
        )
        day3_status = await async_client.get(
            f"/api/tasks/{tasks[2].id}/codespace/status",
            headers=headers,
        )

    assert day3_repo != legacy_day2.repo_full_name
    assert day2_status.status_code == 200, day2_status.text
    assert day2_status.json()["repoFullName"] == legacy_day2.repo_full_name
    assert day3_status.status_code == 200, day3_status.text
    assert day3_status.json()["repoFullName"] == day3_repo
    assert calls["create"] == 1

    workspace_groups = (
        (
            await async_session.execute(
                select(WorkspaceGroup).where(
                    WorkspaceGroup.candidate_session_id == cs.id
                )
            )
        )
        .scalars()
        .all()
    )
    workspaces = (
        (
            await async_session.execute(
                select(Workspace).where(Workspace.candidate_session_id == cs.id)
            )
        )
        .scalars()
        .all()
    )

    assert workspace_groups == []
    assert len(workspaces) == 2
    assert {ws.task_id for ws in workspaces} == {tasks[1].id, tasks[2].id}
    assert all(ws.workspace_group_id is None for ws in workspaces)
