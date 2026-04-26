from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_run_day3_uses_day2_canonical_repo(
    async_client, async_session, candidate_header_factory, override_dependencies
):
    talent_partner = await create_talent_partner(
        async_session, email="run-shared-repo@sim.com"
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

    calls: dict[str, object] = {"create": 0, "run_repos": []}

    class StubGithubClient:
        async def create_empty_repo(
            self, *, owner, repo_name, private=True, default_branch="main"
        ):
            calls["create"] = int(calls["create"]) + 1
            return {
                "owner": {"login": owner},
                "name": repo_name,
                "full_name": f"{owner}/{repo_name}",
                "id": 850 + int(calls["create"]),
                "default_branch": default_branch,
            }

        async def get_file_contents(self, *_a, **_k):
            raise GithubError("missing", status_code=404)

        async def get_branch(self, repo_full_name: str, branch: str):
            return {"commit": {"sha": "base-sha"}}

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

        async def update_ref(self, *_a, **_k):
            return {"ref": "refs/heads/main", "sha": "commit-sha"}

        async def create_codespace(self, *_a, **_k):
            return {
                "name": "codespace-1",
                "state": "available",
                "web_url": "https://codespace.example",
            }

        async def add_collaborator(
            self, repo_full_name: str, username: str, *, permission: str = "push"
        ):
            return {"ok": True}

    class StubActionsRunner:
        async def dispatch_and_wait(self, *, repo_full_name: str, ref: str, inputs):
            calls["run_repos"].append(repo_full_name)
            return ActionsRunResult(
                status="passed",
                run_id=456,
                conclusion="success",
                passed=1,
                failed=0,
                total=1,
                stdout="ok",
                stderr=None,
                head_sha="run-sha",
                html_url="https://example.com/run/456",
                raw=None,
            )

    with override_dependencies(
        {
            candidate_submissions.get_github_client: lambda: StubGithubClient(),
            candidate_submissions.get_actions_runner: lambda: StubActionsRunner(),
        }
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

        day3_run = await async_client.post(
            f"/api/tasks/{tasks[2].id}/run",
            headers=headers,
            json={},
        )

    assert day3_run.status_code == 200, day3_run.text
    assert day3_run.json()["commitSha"] == "run-sha"
    assert calls["create"] == 1
    assert calls["run_repos"] == [day2_repo]
