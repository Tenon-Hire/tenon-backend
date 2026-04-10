from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_candidate_progress_load_tasks_returns_tasks(monkeypatch):
    task = SimpleNamespace(id=101, day_index=1, type="code")
    monkeypatch.setattr(cs_progress.cs_repo, "tasks_for_trial", _async_return([task]))

    tasks = await cs_progress.load_tasks(object(), 1)
    assert tasks == [task]
