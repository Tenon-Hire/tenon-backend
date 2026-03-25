from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_jobs_repository_claim_next_runnable_race_branch():
    class _ClaimResult:
        def __init__(self, *, first_row=None, rowcount=0):
            self._first = first_row
            self.rowcount = rowcount

        def first(self):
            return self._first

    class _ClaimDB:
        def __init__(self):
            self.calls = 0
            self.rollback_count = 0

        async def execute(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                return _ClaimResult(first_row=SimpleNamespace(id="job-1", attempt=0))
            return _ClaimResult(rowcount=0)

        async def commit(self):
            return None

        async def rollback(self):
            self.rollback_count += 1

    claim_db = _ClaimDB()
    claimed = await jobs_repo.claim_next_runnable(
        claim_db,
        worker_id="worker-1",
        now=datetime.now(UTC),
        lease_seconds=30,
    )
    assert claimed is None
    assert claim_db.rollback_count == 1
