from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_workspace_creation_service_utils import *


@pytest.mark.asyncio
async def test_provision_workspace_non_group_path(monkeypatch):
    db = object()
    candidate_session = SimpleNamespace(id=11)
    task = SimpleNamespace(id=101, day_index=1, type="design")
    now = datetime.now(UTC)
    github_client = object()
    calls: dict[str, object] = {}
    created = SimpleNamespace(
        id="ws-1",
        repo_full_name="org/repo",
        default_branch="main",
        base_template_sha="base-sha",
        precommit_sha=None,
    )

    async def _generate_template_repo(**_kwargs):
        return ("org/template", "org/repo", "main", 123)

    async def _fetch_base_template_sha(_client, _repo, _branch):
        return "base-sha"

    async def _add_collaborator_if_needed(_client, _repo, _username):
        calls["collaborator"] = True

    async def _create_workspace(_db, **kwargs):
        calls["create_workspace"] = kwargs
        return created

    monkeypatch.setattr(wc, "generate_template_repo", _generate_template_repo)
    monkeypatch.setattr(wc, "fetch_base_template_sha", _fetch_base_template_sha)
    monkeypatch.setattr(wc, "add_collaborator_if_needed", _add_collaborator_if_needed)
    monkeypatch.setattr(wc.workspace_repo, "create_workspace", _create_workspace)

    result = await wc.provision_workspace(
        db,
        candidate_session=candidate_session,
        task=task,
        github_client=github_client,
        github_username="octocat",
        repo_prefix="pref-",
        destination_owner="org",
        now=now,
    )

    assert result is created
    assert calls["collaborator"] is True
    assert calls["create_workspace"] == {
        "candidate_session_id": candidate_session.id,
        "task_id": task.id,
        "template_repo_full_name": "org/template",
        "repo_full_name": "org/repo",
        "repo_id": 123,
        "default_branch": "main",
        "base_template_sha": "base-sha",
        "codespace_url": "https://codespaces.new/org/repo?quickstart=1",
        "created_at": now,
    }
