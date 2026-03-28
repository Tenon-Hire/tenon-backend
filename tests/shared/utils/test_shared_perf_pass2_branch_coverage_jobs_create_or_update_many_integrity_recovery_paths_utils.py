from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_jobs_create_or_update_many_integrity_recovery_paths(monkeypatch):
    specs = [
        jobs_repo.IdempotentJobSpec(
            job_type="batch_type_a",
            idempotency_key="batch-key-a",
            payload_json={"a": 1},
        ),
        jobs_repo.IdempotentJobSpec(
            job_type="batch_type_b",
            idempotency_key="batch-key-b",
            payload_json={"b": 1},
        ),
        jobs_repo.IdempotentJobSpec(
            job_type="batch_type_c",
            idempotency_key="batch-key-c",
            payload_json={"c": 1},
        ),
    ]

    async def _load_for_keys(*_args, **_kwargs):
        return {}

    load_one_values = iter(
        [
            SimpleNamespace(id="existing-a"),  # First spec resolves immediately.
            None,  # Second spec enters nested insert path.
            SimpleNamespace(id="existing-b"),  # Second spec conflict recovery.
            None,  # Third spec enters nested insert path and succeeds.
        ]
    )

    async def _load_one(*_args, **_kwargs):
        return next(load_one_values)

    monkeypatch.setattr(jobs_repo, "_load_idempotent_jobs_for_keys", _load_for_keys)
    monkeypatch.setattr(jobs_repo, "_load_idempotent_job", _load_one)

    class _Nested:
        def __init__(self, db):
            self.db = db

        async def __aenter__(self):
            self.db.in_nested = True
            return self

        async def __aexit__(self, exc_type, exc, tb):
            self.db.in_nested = False
            return False

    class _DB:
        def __init__(self):
            self.in_nested = False
            self.nested_flush_calls = 0
            self.final_flush_calls = 0
            self.added = []

        async def execute(self, *_args, **_kwargs):
            raise IntegrityError("insert", {}, RuntimeError("race"))

        def begin_nested(self):
            return _Nested(self)

        def add(self, obj):
            self.added.append(obj)

        async def flush(self):
            if self.in_nested:
                self.nested_flush_calls += 1
                if self.nested_flush_calls == 1:
                    raise IntegrityError("nested", {}, RuntimeError("race"))
            else:
                self.final_flush_calls += 1

    db = _DB()
    resolved = await jobs_repo.create_or_update_many_idempotent(
        db,
        company_id=1,
        jobs=specs,
        commit=False,
    )
    assert len(resolved) == 3
    assert db.nested_flush_calls == 2
    assert db.final_flush_calls == 1
    assert len(db.added) == 2
