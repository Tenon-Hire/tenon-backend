from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_jobs_create_or_get_commit_integrity_reraises_when_not_recoverable(
    monkeypatch,
):
    async def _load_none(*_args, **_kwargs):
        return None

    class _DB:
        def add(self, _obj):
            return None

        async def commit(self):
            raise IntegrityError("insert", {}, RuntimeError("duplicate"))

        async def rollback(self):
            return None

        async def refresh(self, _obj):
            raise AssertionError("refresh should not run on failed commit")

    monkeypatch.setattr(jobs_repo, "_load_idempotent_job", _load_none)
    with pytest.raises(IntegrityError):
        await jobs_repo.create_or_get_idempotent(
            _DB(),
            job_type="branch_job",
            idempotency_key="branch-key-commit-error",
            payload_json={"a": 1},
            company_id=1,
            commit=True,
        )
