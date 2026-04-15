from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_workspace_creation_service_utils import *


@pytest.mark.asyncio
async def test_provision_workspace_coding_task_uses_legacy_path_when_grouping_disabled(
    monkeypatch,
):
    candidate_session = SimpleNamespace(id=11)
    task = SimpleNamespace(id=101, day_index=2, type="code")
    now = datetime.now(UTC)
    calls: dict[str, object] = {}
    created = SimpleNamespace(
        id="ws-legacy",
        repo_full_name="org/day3",
        default_branch="main",
        base_template_sha="base-sha",
        precommit_sha=None,
    )

    async def _session_uses_grouped_workspace(*_args, **_kwargs):
        return False

    async def _generate_template_repo(**_kwargs):
        return ("org/template", "org/day3", "main", 456)

    async def _fetch_base_template_sha(_client, _repo, _branch):
        return "base-sha"

    async def _add_collaborator_if_needed(_client, _repo, _username):
        calls["collaborator"] = True

    async def _create_workspace(_db, **kwargs):
        calls["create_workspace"] = kwargs
        return created

    async def _provision_grouped_workspace(*_args, **_kwargs):
        raise AssertionError("Grouped path should be skipped for legacy sessions")

    monkeypatch.setattr(
        wc.workspace_repo,
        "session_uses_grouped_workspace",
        _session_uses_grouped_workspace,
    )
    monkeypatch.setattr(wc, "generate_template_repo", _generate_template_repo)
    monkeypatch.setattr(wc, "fetch_base_template_sha", _fetch_base_template_sha)
    monkeypatch.setattr(wc, "add_collaborator_if_needed", _add_collaborator_if_needed)
    monkeypatch.setattr(wc.workspace_repo, "create_workspace", _create_workspace)
    monkeypatch.setattr(
        wc, "_provision_grouped_workspace", _provision_grouped_workspace
    )

    result = await wc.provision_workspace(
        object(),
        candidate_session=candidate_session,
        task=task,
        github_client=object(),
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
        "repo_full_name": "org/day3",
        "repo_id": 456,
        "default_branch": "main",
        "base_template_sha": "base-sha",
        "codespace_url": "https://codespaces.new/org/day3?quickstart=1",
        "created_at": now,
    }
