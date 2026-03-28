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


@pytest.mark.asyncio
async def test_submit_workspace_falls_back_to_task_lookup_when_workspace_key_missing(
    monkeypatch,
):
    workspace = SimpleNamespace(default_branch="main")
    calls = {"task_lookup": 0}

    class _WorkspaceRepo:
        async def get_by_session_and_task(self, *_args, **_kwargs):
            calls["task_lookup"] += 1
            return workspace if calls["task_lookup"] == 2 else None

        async def get_by_session_and_workspace_key(self, *_args, **_kwargs):
            raise AssertionError(
                "grouped key lookup should not run without workspace key"
            )

    monkeypatch.setattr(
        submit_workspace_use_case.submission_service,
        "workspace_repo",
        _WorkspaceRepo(),
    )
    monkeypatch.setattr(
        submit_workspace_use_case,
        "resolve_workspace_key",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        submit_workspace_use_case.submission_service,
        "validate_branch",
        lambda branch: branch,
    )

    found, branch = await fetch_workspace_and_branch(
        object(),
        candidate_session_id=11,
        task_id=22,
        payload=SimpleNamespace(branch=None),
        task_day_index=2,
        task_type="code",
    )
    assert found is workspace
    assert branch == "main"
    assert calls["task_lookup"] == 2
