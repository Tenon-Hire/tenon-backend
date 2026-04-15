from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_workspace_creation_service_utils import *


@pytest.mark.asyncio
async def test_provision_workspace_persists_precommit_sha_when_bundle_applied(
    monkeypatch,
):
    candidate_session = SimpleNamespace(id=11, scenario_version_id=2)
    task = SimpleNamespace(id=101, day_index=2, type="code")
    now = datetime.now(UTC)
    workspace = SimpleNamespace(
        id="ws-1",
        repo_full_name="org/repo",
        default_branch="main",
        base_template_sha="base-sha",
        precommit_sha=None,
    )
    calls: dict[str, object] = {}

    async def _generate_template_repo(**_kwargs):
        return ("org/template", "org/repo", "main", 123)

    async def _fetch_base_template_sha(_client, _repo, _branch):
        return "base-sha"

    async def _create_workspace(_db, **_kwargs):
        return workspace

    async def _session_uses_grouped_workspace(*_args, **_kwargs):
        return False

    async def _apply_bundle(*_args, **_kwargs):
        return SimpleNamespace(
            state="applied",
            precommit_sha="precommit-sha-123",
            bundle_id=88,
        )

    async def _add_collaborator_if_needed(*_args, **_kwargs):
        return None

    async def _set_precommit_sha(_db, *, workspace, precommit_sha):
        calls["set_precommit_sha"] = precommit_sha
        workspace.precommit_sha = precommit_sha
        return workspace

    monkeypatch.setattr(wc, "generate_template_repo", _generate_template_repo)
    monkeypatch.setattr(wc, "fetch_base_template_sha", _fetch_base_template_sha)
    monkeypatch.setattr(
        wc.workspace_repo,
        "session_uses_grouped_workspace",
        _session_uses_grouped_workspace,
    )
    monkeypatch.setattr(wc.workspace_repo, "create_workspace", _create_workspace)
    monkeypatch.setattr(wc, "add_collaborator_if_needed", _add_collaborator_if_needed)
    monkeypatch.setattr(wc, "apply_precommit_bundle_if_available", _apply_bundle)
    monkeypatch.setattr(wc.workspace_repo, "set_precommit_sha", _set_precommit_sha)

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

    assert result.precommit_sha == "precommit-sha-123"
    assert calls["set_precommit_sha"] == "precommit-sha-123"
