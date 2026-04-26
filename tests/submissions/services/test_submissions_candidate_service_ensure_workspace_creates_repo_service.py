from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_candidate_service_utils import *


@pytest.mark.asyncio
async def test_ensure_workspace_creates_repo(async_session):
    talent_partner = await create_talent_partner(async_session, email="ws@sim.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim, status="in_progress")

    class StubGithubClient:
        async def create_empty_repo(
            self, *, owner, repo_name, private=True, default_branch="main"
        ):
            return {
                "owner": {"login": owner},
                "name": repo_name,
                "full_name": f"{owner}/{repo_name}",
                "id": 5,
                "default_branch": default_branch,
            }

        async def get_file_contents(self, *_args, **_kwargs):
            raise GithubError("missing", status_code=404)

        async def add_collaborator(
            self, repo_full_name, username, *, permission="push"
        ):
            return {"invited": username}

        async def get_branch(self, repo_full_name, branch):
            return {"commit": {"sha": "base-sha"}}

        async def create_blob(self, _repo_full_name, *, content):
            return {"sha": "blob-sha"}

        async def create_tree(self, _repo_full_name, *, tree, base_tree=None):
            return {"sha": "tree-sha"}

        async def create_commit(self, _repo_full_name, *, message, tree, parents):
            return {"sha": "commit-sha"}

        async def create_ref(self, _repo_full_name, *, ref, sha):
            return {"ref": ref, "sha": sha}

        async def update_ref(self, _repo_full_name, *, ref, sha, force=False):
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
                "name": "codespace-1",
                "state": "available",
                "web_url": "https://codespace.example",
            }

    ws = await svc.ensure_workspace(
        async_session,
        candidate_session=cs,
        task=tasks[1],
        github_client=StubGithubClient(),
        github_username="octocat",
        repo_prefix="prefix-",
        destination_owner="org",
        now=datetime.now(UTC),
    )
    assert ws.repo_full_name == f"org/prefix-{cs.id}-coding"
    assert ws.base_template_sha == "commit-sha"


@pytest.mark.asyncio
async def test_ensure_workspace_requires_username_for_empty_repo(async_session):
    talent_partner = await create_talent_partner(async_session, email="ws2@sim.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim, status="in_progress")

    class StubGithubClient:
        async def create_empty_repo(self, **_kw):
            raise AssertionError(
                "empty repo creation should be gated before GitHub calls"
            )

    with pytest.raises(HTTPException) as excinfo:
        await svc.ensure_workspace(
            async_session,
            candidate_session=cs,
            task=tasks[1],
            github_client=StubGithubClient(),
            github_username="",
            repo_prefix="prefix-",
            destination_owner="org",
            now=datetime.now(UTC),
            bootstrap_empty_repo=True,
        )

    assert excinfo.value.status_code == 400
    assert getattr(excinfo.value, "error_code", None) == "GITHUB_USERNAME_REQUIRED"
