from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_workspace_creation_service_utils import *


@pytest.mark.asyncio
async def test_provision_workspace_coding_task_uses_grouped_path_when_eligible(
    monkeypatch,
):
    candidate_session = SimpleNamespace(id=11)
    task = SimpleNamespace(id=101, day_index=2, type="code")
    created = SimpleNamespace(id="ws-grouped")
    calls: dict[str, int] = {"grouped": 0}

    async def _session_uses_grouped_workspace(*_args, **_kwargs):
        return True

    async def _provision_grouped_workspace(*_args, **_kwargs):
        calls["grouped"] += 1
        return created

    monkeypatch.setattr(
        wc.workspace_repo,
        "session_uses_grouped_workspace",
        _session_uses_grouped_workspace,
    )
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

    assert result is created
    assert calls["grouped"] == 1
