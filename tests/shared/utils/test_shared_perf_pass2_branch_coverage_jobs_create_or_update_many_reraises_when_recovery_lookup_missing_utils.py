from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_jobs_create_or_update_many_reraises_when_recovery_lookup_missing(
    monkeypatch,
):
    specs = [
        jobs_repo.IdempotentJobSpec(
            job_type="batch_type_recover",
            idempotency_key="batch-key-recover",
            payload_json={"x": 1},
        )
    ]

    async def _load_for_keys(*_args, **_kwargs):
        return {}

    async def _load_none(*_args, **_kwargs):
        return None

    monkeypatch.setattr(jobs_repo, "_load_idempotent_jobs_for_keys", _load_for_keys)
    monkeypatch.setattr(jobs_repo, "_load_idempotent_job", _load_none)

    class _Nested:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _DB:
        async def execute(self, *_args, **_kwargs):
            raise IntegrityError("insert", {}, RuntimeError("race"))

        def begin_nested(self):
            return _Nested()

        def add(self, _obj):
            return None

        async def flush(self):
            raise IntegrityError("nested", {}, RuntimeError("race"))

    with pytest.raises(IntegrityError):
        await jobs_repo.create_or_update_many_idempotent(
            _DB(),
            company_id=1,
            jobs=specs,
            commit=False,
        )
