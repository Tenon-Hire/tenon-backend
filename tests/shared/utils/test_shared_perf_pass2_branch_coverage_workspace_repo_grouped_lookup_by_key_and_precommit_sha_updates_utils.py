from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_workspace_repo_grouped_lookup_by_key_and_precommit_sha_updates(
    monkeypatch,
):
    grouped_workspace = SimpleNamespace(id="ws-grouped")

    async def _group_lookup(*_args, **_kwargs):
        return grouped_workspace

    monkeypatch.setattr(
        workspace_repo, "get_by_session_and_workspace_key", _group_lookup
    )

    resolution = workspace_repo.WorkspaceResolution(
        workspace_key="day-2-code",
        uses_grouped_workspace=True,
        workspace_group=None,
        workspace_group_checked=False,
    )
    found = await workspace_repo.get_by_session_and_task(
        object(),
        candidate_session_id=1,
        task_id=2,
        workspace_resolution=resolution,
    )
    assert found is grouped_workspace

    class _DB:
        def __init__(self):
            self.commits = 0
            self.flushes = 0
            self.refreshes = 0

        async def commit(self):
            self.commits += 1

        async def flush(self):
            self.flushes += 1

        async def refresh(self, _workspace):
            self.refreshes += 1

    db = _DB()
    workspace = SimpleNamespace(
        precommit_sha=None, precommit_details_json='{"no_bundle":true}'
    )
    updated = await workspace_repo.set_precommit_sha(
        db,
        workspace=workspace,
        precommit_sha="sha-1",
        commit=True,
        refresh=True,
    )
    assert updated.precommit_sha == "sha-1"
    assert updated.precommit_details_json is None
    assert db.commits == 1
    assert db.refreshes == 1

    updated = await workspace_repo.set_precommit_sha(
        db,
        workspace=workspace,
        precommit_sha="sha-2",
        commit=False,
        refresh=False,
    )
    assert updated.precommit_sha == "sha-2"
    assert db.flushes == 1
