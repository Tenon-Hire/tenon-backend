from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_workspace_creation_service_utils import *


@pytest.mark.asyncio
async def test_provision_workspace_day3_uses_existing_coding_group(monkeypatch):
    candidate_session = SimpleNamespace(id=11)
    task = SimpleNamespace(id=101, day_index=3, type="code")
    grouped_workspace = SimpleNamespace(id="ws-grouped")
    calls = {"grouped": 0}

    async def _session_uses_grouped_workspace(*_args, **_kwargs):
        return True

    async def _get_workspace_group(*_args, **_kwargs):
        return SimpleNamespace(id="group-1")

    async def _provision_grouped_workspace(*_args, **_kwargs):
        calls["grouped"] += 1
        return grouped_workspace

    monkeypatch.setattr(
        wc.workspace_repo,
        "session_uses_grouped_workspace",
        _session_uses_grouped_workspace,
    )
    monkeypatch.setattr(wc.workspace_repo, "get_workspace_group", _get_workspace_group)
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
        now=datetime.now(UTC),
    )

    assert result is grouped_workspace
    assert calls["grouped"] == 1
