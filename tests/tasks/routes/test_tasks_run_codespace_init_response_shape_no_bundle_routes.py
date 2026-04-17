from __future__ import annotations

import pytest

from app.config import settings
from app.integrations.github import GithubError
from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_codespace_init_response_shape_no_bundle(
    async_client, async_session, candidate_header_factory, override_dependencies
):
    talent_partner = await create_talent_partner(
        async_session, email="init-shape@sim.com"
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

    class StubGithubClient:
        async def create_empty_repo(
            self, *, owner, repo_name, private=True, default_branch="main"
        ):
            return {
                "owner": {"login": owner},
                "name": repo_name,
                "full_name": f"{owner}/{repo_name}",
                "id": 909,
                "default_branch": default_branch,
            }

        async def get_file_contents(self, *_args, **_kwargs):
            raise GithubError("missing", status_code=404)

        async def get_branch(self, repo_full_name: str, branch: str):
            return {"commit": {"sha": "base-sha-shape"}}

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
            return {
                "name": "codespace-909",
                "state": "available",
                "web_url": "https://codespace-909.github.dev",
            }

        async def add_collaborator(
            self, repo_full_name: str, username: str, *, permission: str = "push"
        ):
            return {"ok": True}

    with override_dependencies(
        {candidate_submissions.get_github_client: lambda: StubGithubClient()}
    ):
        headers = candidate_header_factory(cs)
        resp = await async_client.post(
            f"/api/tasks/{tasks[1].id}/codespace/init",
            headers=headers,
            json={"githubUsername": "octocat"},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    expected_repo_name = f"{settings.github.GITHUB_REPO_PREFIX}{cs.id}"
    expected_repo_full_name = f"{settings.github.GITHUB_ORG}/{expected_repo_name}"
    assert body == {
        "repoFullName": expected_repo_full_name,
        "codespaceUrl": "https://codespace-909.github.dev",
        "codespaceState": "available",
        "defaultBranch": "main",
        "workspaceId": body["workspaceId"],
    }
    assert isinstance(body["workspaceId"], str)
    assert body["workspaceId"]

    workspace = await workspace_repo.get_by_session_and_task(
        async_session,
        candidate_session_id=cs.id,
        task_id=tasks[1].id,
    )
    assert workspace is not None
    assert workspace.precommit_sha is None
    assert workspace.precommit_details_json is None
