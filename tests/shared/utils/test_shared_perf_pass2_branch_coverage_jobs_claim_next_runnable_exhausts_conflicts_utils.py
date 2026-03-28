from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_jobs_claim_next_runnable_exhausts_conflicts(monkeypatch):
    del monkeypatch  # unused, retained for consistent test signature style

    class _ClaimResult:
        def __init__(self, *, first_row=None, rowcount=0):
            self._first = first_row
            self.rowcount = rowcount

        def first(self):
            return self._first

    class _DB:
        def __init__(self):
            self.calls = 0
            self.rollbacks = 0
            self.commits = 0

        async def execute(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls % 2 == 1:
                return _ClaimResult(first_row=SimpleNamespace(id="job-1", attempt=0))
            return _ClaimResult(rowcount=0)

        async def rollback(self):
            self.rollbacks += 1

        async def commit(self):
            self.commits += 1

    db = _DB()
    claimed = await jobs_repo.claim_next_runnable(
        db,
        worker_id="worker-conflict",
        now=datetime.now(UTC),
        lease_seconds=30,
    )
    assert claimed is None
    assert db.rollbacks == 8
    assert db.commits == 0
