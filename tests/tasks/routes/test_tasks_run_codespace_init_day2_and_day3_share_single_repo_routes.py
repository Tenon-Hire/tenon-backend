from __future__ import annotations

import pytest

from app.integrations.github import GithubError
from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_codespace_init_day2_and_day3_share_single_repo(
    async_client, async_session, candidate_header_factory, override_dependencies
):
    talent_partner = await create_talent_partner(
        async_session, email="shared-repo@sim.com"
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

    calls: dict[str, int] = {"generate": 0}

    class StubGithubClient:
        async def create_empty_repo(
            self, *, owner, repo_name, private=True, default_branch="main"
        ):
            calls["repo"] = calls.get("repo", 0) + 1
            return {
                "owner": {"login": owner},
                "name": repo_name,
                "full_name": f"{owner}/{repo_name}",
                "id": 600 + calls["repo"],
                "default_branch": default_branch,
            }

        async def get_file_contents(self, *_args, **_kwargs):
            raise GithubError("missing", status_code=404)

        async def add_collaborator(
            self, repo_full_name: str, username: str, *, permission: str = "push"
        ):
            return {"ok": True}

        async def get_branch(self, repo_full_name: str, branch: str):
            return {"commit": {"sha": "base-sha"}}

        async def create_tree(self, repo_full_name, *, tree, base_tree=None):
            return {"sha": "tree-sha"}

        async def create_commit(self, repo_full_name, *, message, tree, parents):
            return {"sha": "commit-sha"}

        async def create_ref(self, repo_full_name, *, ref, sha):
            return {"ref": ref, "sha": sha}

        async def update_ref(self, repo_full_name, *, ref, sha, force=False):
            return {"ref": ref, "sha": sha, "force": force}

        async def create_codespace(
            self,
            repo_full_name,
            *,
            ref=None,
            devcontainer_path=None,
            machine=None,
            location=None,
        ):
            calls["codespace"] = calls.get("codespace", 0) + 1
            return {
                "name": f"codespace-{calls['codespace']}",
                "state": "available",
                "web_url": f"https://codespace-{calls['codespace']}.github.dev",
            }

    with override_dependencies(
        {candidate_submissions.get_github_client: lambda: StubGithubClient()}
    ):
        headers = candidate_header_factory(cs)
        day2_init = await async_client.post(
            f"/api/tasks/{tasks[1].id}/codespace/init",
            headers=headers,
            json={"githubUsername": "octocat"},
        )
        assert day2_init.status_code == 200, day2_init.text
        day2_repo = day2_init.json()["repoFullName"]

        await create_submission(
            async_session, candidate_session=cs, task=tasks[1], content_text="day2"
        )
        await async_session.commit()

        day3_init = await async_client.post(
            f"/api/tasks/{tasks[2].id}/codespace/init",
            headers=headers,
            json={"githubUsername": "octocat"},
        )

    assert day3_init.status_code == 200, day3_init.text
    assert day3_init.json()["repoFullName"] == day2_repo
    assert calls["repo"] == 1
    assert calls["codespace"] == 1

    groups = (
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
    assert len(groups) == 1
    assert groups[0].workspace_key == "coding"
    assert len(workspaces) == 1
    assert workspaces[0].repo_full_name == day2_repo
