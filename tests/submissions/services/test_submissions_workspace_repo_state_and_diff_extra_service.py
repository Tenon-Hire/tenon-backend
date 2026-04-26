from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.integrations.github.client import GithubError
from app.submissions.services import (
    submissions_services_submissions_workspace_repo_state_service as repo_state,
)
from app.submissions.services.use_cases import (
    submissions_services_use_cases_submissions_use_cases_submit_diff_service as submit_diff,
)


class _Github:
    def __init__(self):
        self.added: list[tuple[str, str]] = []

    async def get_branch(self, repo_full_name, branch):
        assert repo_full_name == "org/repo"
        assert branch == "feature"
        return {"commit": {"sha": "branch-sha"}}

    async def get_compare(self, repo_full_name, base, head):
        assert repo_full_name == "org/repo"
        return {"base": base, "head": head, "files": [{"filename": "README.md"}]}

    async def add_collaborator(self, repo_full_name, github_username):
        self.added.append((repo_full_name, github_username))


@pytest.mark.asyncio
async def test_build_diff_summary_uses_branch_sha_when_bootstrap_sha_missing():
    github = _Github()
    workspace = SimpleNamespace(repo_full_name="org/repo", bootstrap_commit_sha=None)

    summary = await submit_diff.build_diff_summary(
        github, workspace, "feature", "head-sha"
    )

    payload = json.loads(summary)
    assert payload["base"] == "branch-sha"
    assert payload["head"] == "head-sha"


@pytest.mark.asyncio
async def test_fetch_bootstrap_commit_sha_and_collaborator_helpers():
    github = _Github()

    assert (
        await repo_state.fetch_bootstrap_commit_sha(github, "org/repo", "feature")
        == "branch-sha"
    )
    await repo_state.add_collaborator_if_needed(github, "org/repo", "octocat")
    await repo_state.add_collaborator_if_needed(github, "org/repo", None)
    assert github.added == [("org/repo", "octocat")]


@pytest.mark.asyncio
async def test_fetch_bootstrap_commit_sha_returns_none_on_github_error():
    class Github:
        async def get_branch(self, *_args, **_kwargs):
            raise GithubError("unavailable")

    assert (
        await repo_state.fetch_bootstrap_commit_sha(Github(), "org/repo", None) is None
    )


@pytest.mark.asyncio
async def test_ensure_repo_is_active_unarchives_when_supported():
    class Github:
        async def get_repo(self, repo_full_name):
            assert repo_full_name == "org/repo"
            return {"archived": True}

        async def unarchive_repo(self, repo_full_name):
            assert repo_full_name == "org/repo"
            return {"archived": False, "full_name": repo_full_name}

    assert await repo_state.ensure_repo_is_active(Github(), "org/repo") == {
        "archived": False,
        "full_name": "org/repo",
    }


@pytest.mark.asyncio
async def test_refresh_codespace_state_persists_changed_state(monkeypatch):
    workspace = SimpleNamespace(
        repo_full_name="org/repo",
        codespace_name="space",
        codespace_state="starting",
    )

    class Github:
        async def get_codespace(self, repo_full_name, codespace_name):
            assert repo_full_name == "org/repo"
            assert codespace_name == "space"
            return {"state": "Available"}

    async def _set_state(db, *, workspace, codespace_state):
        assert db == "db"
        workspace.codespace_state = codespace_state
        return workspace

    monkeypatch.setattr(
        repo_state.workspace_mutations_repo, "set_codespace_state", _set_state
    )

    refreshed = await repo_state.refresh_codespace_state(
        "db", workspace=workspace, github_client=Github()
    )

    assert refreshed.codespace_state == "available"
