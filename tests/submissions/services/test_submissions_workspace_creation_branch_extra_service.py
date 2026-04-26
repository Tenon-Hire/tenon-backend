from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.submissions.services import (
    submissions_services_submissions_workspace_creation_group_repo_create_service as group_create,
)
from app.submissions.services import (
    submissions_services_submissions_workspace_creation_grouped_hydration_service as hydration,
)


@pytest.mark.asyncio
async def test_create_group_repo_uses_candidate_repo_name_for_empty_bootstrap(
    monkeypatch,
):
    calls: dict[str, object] = {}

    async def _bootstrap(**kwargs):
        calls.update(kwargs)
        return SimpleNamespace(repo_full_name="org/repo")

    monkeypatch.setattr(group_create, "bootstrap_empty_candidate_repo", _bootstrap)
    monkeypatch.setattr(
        group_create, "build_candidate_repo_name", lambda prefix, cs: f"{prefix}{cs.id}"
    )

    result = await group_create.create_group_repo(
        candidate_session=SimpleNamespace(id=9),
        task=SimpleNamespace(id=2),
        workspace_key="coding",
        github_client=object(),
        repo_prefix="repo-",
        destination_owner="org",
        bootstrap_empty_repo=True,
        trial=object(),
        scenario_version=object(),
    )

    assert result.repo_full_name == "org/repo"
    assert calls["repo_name"] == "repo-9"


@pytest.mark.asyncio
async def test_hydrate_existing_workspace_adds_collaborator_when_requested(monkeypatch):
    added: list[tuple[str, str | None]] = []
    workspace = SimpleNamespace(repo_full_name="org/repo")

    async def _add(_github_client, repo_full_name, github_username):
        added.append((repo_full_name, github_username))

    monkeypatch.setattr(hydration, "add_collaborator_if_needed", _add)

    assert (
        await hydration.hydrate_existing_workspace(
            "db",
            workspace,
            SimpleNamespace(id=1),
            SimpleNamespace(id=2),
            object(),
            "octocat",
            hydrate_bundle=False,
            commit=False,
            ensure_collaborator=True,
        )
        is workspace
    )
    assert added == [("org/repo", "octocat")]
