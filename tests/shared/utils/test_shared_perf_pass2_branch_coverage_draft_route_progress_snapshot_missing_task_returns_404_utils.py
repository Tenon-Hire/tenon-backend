from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_draft_route_progress_snapshot_missing_task_returns_404(monkeypatch):
    async def _snapshot(*_args, **_kwargs):
        return ([], set(), None, 0, 0, False)

    monkeypatch.setattr(draft_route.cs_service, "progress_snapshot", _snapshot)

    with pytest.raises(HTTPException) as excinfo:
        await draft_route.put_task_draft_route(
            task_id=9,
            payload=TaskDraftUpsertRequest(contentText="x", contentJson=None),
            candidate_session=SimpleNamespace(id=1, trial_id=2),
            db=SimpleNamespace(),
        )
    assert excinfo.value.status_code == 404
