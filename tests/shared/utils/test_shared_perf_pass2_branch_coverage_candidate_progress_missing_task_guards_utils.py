from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_candidate_progress_missing_task_guards(monkeypatch):
    monkeypatch.setattr(cs_progress.cs_repo, "tasks_for_trial", _async_return([]))
    with pytest.raises(HTTPException) as excinfo:
        await cs_progress.load_tasks(object(), 123)
    assert excinfo.value.status_code == 500

    class _NoRowsDB:
        async def execute(self, *_args, **_kwargs):
            return _RowsResult(rows=[])

    with pytest.raises(HTTPException) as excinfo2:
        await cs_progress.load_tasks_with_completion_state(
            _NoRowsDB(),
            trial_id=123,
            candidate_session_id=456,
        )
    assert excinfo2.value.status_code == 500
