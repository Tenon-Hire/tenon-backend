from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.submissions.repositories.github_native.workspaces import (
    submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_lookup_repository as lookup_repo,
)
from app.submissions.repositories.github_native.workspaces.submissions_repositories_github_native_workspaces_submissions_github_native_workspaces_repository_model import (
    WorkspaceResolution,
)


class _NoExecuteDB:
    async def execute(self, _stmt):
        raise AssertionError(
            "execute should not be called for grouped-workspace lookups"
        )


@pytest.mark.asyncio
async def test_get_by_session_and_task_impl_returns_none_when_group_lookup_misses():
    db = _NoExecuteDB()
    resolution = WorkspaceResolution(
        workspace_key=None,
        uses_grouped_workspace=True,
        workspace_group=SimpleNamespace(id="wg-1"),
        workspace_group_checked=True,
    )

    async def _resolve_workspace_resolution(*_args, **_kwargs):
        raise AssertionError("resolution was provided and should not be resolved")

    async def _get_by_workspace_group_id(*_args, **_kwargs):
        return None

    async def _get_by_session_and_workspace_key(*_args, **_kwargs):
        raise AssertionError("key lookup should not run when group lookup path is used")

    found = await lookup_repo.get_by_session_and_task_impl(
        db,
        candidate_session_id=101,
        task_id=202,
        workspace_resolution=resolution,
        resolve_workspace_resolution=_resolve_workspace_resolution,
        get_by_workspace_group_id=_get_by_workspace_group_id,
        get_by_session_and_workspace_key=_get_by_session_and_workspace_key,
    )

    assert found is None


@pytest.mark.asyncio
async def test_get_by_session_and_task_impl_returns_none_when_key_lookup_misses():
    db = _NoExecuteDB()
    resolution = WorkspaceResolution(
        workspace_key="coding",
        uses_grouped_workspace=True,
        workspace_group=None,
        workspace_group_checked=False,
    )

    async def _resolve_workspace_resolution(*_args, **_kwargs):
        raise AssertionError("resolution was provided and should not be resolved")

    async def _get_by_workspace_group_id(*_args, **_kwargs):
        raise AssertionError("group lookup should not run when no group is attached")

    async def _get_by_session_and_workspace_key(*_args, **_kwargs):
        return None

    found = await lookup_repo.get_by_session_and_task_impl(
        db,
        candidate_session_id=303,
        task_id=404,
        workspace_resolution=resolution,
        resolve_workspace_resolution=_resolve_workspace_resolution,
        get_by_workspace_group_id=_get_by_workspace_group_id,
        get_by_session_and_workspace_key=_get_by_session_and_workspace_key,
    )

    assert found is None
