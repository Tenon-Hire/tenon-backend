from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_submit_workspace_uses_grouped_lookup_when_available(monkeypatch):
    workspace = SimpleNamespace(default_branch="main")

    class _WorkspaceRepo:
        async def get_by_session_and_task(self, *_args, **_kwargs):
            return None

        async def get_by_session_and_workspace_key(self, *_args, **_kwargs):
            return workspace

    monkeypatch.setattr(
        submit_workspace_use_case.submission_service,
        "workspace_repo",
        _WorkspaceRepo(),
    )
    monkeypatch.setattr(
        submit_workspace_use_case.submission_service,
        "validate_branch",
        lambda branch: branch,
    )

    found, branch = await fetch_workspace_and_branch(
        object(),
        candidate_session_id=1,
        task_id=2,
        payload=SimpleNamespace(branch=None),
        task_day_index=2,
        task_type="code",
    )
    assert found is workspace
    assert branch == "main"
