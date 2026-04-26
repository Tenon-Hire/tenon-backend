from __future__ import annotations

import pytest

from app.config import settings
from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_run_tests_maps_github_not_found_error(
    async_client, async_session, candidate_header_factory, override_dependencies
):
    talent_partner = await create_talent_partner(
        async_session, email="run-notfound@sim.com"
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

    class NotFoundRunner:
        async def dispatch_and_wait(self, **_kwargs):
            raise GithubError("missing", status_code=404)

    class StubGithubClient:
        async def create_empty_repo(
            self, *, owner, repo_name, private=True, default_branch="main"
        ):
            return {
                "owner": {"login": owner},
                "name": repo_name,
                "full_name": f"{owner}/{repo_name}",
                "id": 1,
                "default_branch": default_branch,
            }

        async def get_file_contents(self, *_a, **_k):
            raise GithubError("missing", status_code=404)

        async def add_collaborator(self, *_a, **_k):
            return {"ok": True}

        async def get_branch(self, *_a, **_k):
            return {"commit": {"sha": "base"}}

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
                "web_url": "https://example.com/codespace",
            }

        async def get_compare(self, *_a, **_k):
            return {}

    with override_dependencies(
        {
            candidate_submissions.get_actions_runner: lambda: NotFoundRunner(),
            candidate_submissions.get_github_client: lambda: StubGithubClient(),
        }
    ):
        headers = candidate_header_factory(cs)
        init_resp = await async_client.post(
            f"/api/tasks/{tasks[1].id}/codespace/init",
            headers=headers,
            json={"githubUsername": "octocat"},
        )
        assert init_resp.status_code == 200, init_resp.text
        resp = await async_client.post(
            f"/api/tasks/{tasks[1].id}/run",
            headers=headers,
            json={},
        )

    assert resp.status_code == 502
    assert "not found" in resp.json()["detail"].lower()
