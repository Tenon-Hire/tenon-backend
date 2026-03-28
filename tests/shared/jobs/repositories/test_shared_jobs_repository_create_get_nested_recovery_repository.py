from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from app.shared.jobs.repositories import (
    shared_jobs_repositories_repository_create_get_repository as create_get_repo,
)


class _NestedContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _NestedFailureDB:
    def __init__(self):
        self.added = []

    def begin_nested(self):
        return _NestedContext()

    def add(self, job):
        self.added.append(job)

    async def flush(self):
        raise IntegrityError("", {}, None)


@pytest.mark.asyncio
async def test_insert_nested_or_get_existing_returns_loaded_row_on_integrity(
    monkeypatch,
):
    db = _NestedFailureDB()
    existing = SimpleNamespace(id="job-existing")

    async def _load_existing(*_args, **_kwargs):
        return existing

    monkeypatch.setattr(create_get_repo, "load_idempotent_job", _load_existing)

    created = await create_get_repo._insert_nested_or_get_existing(
        db,
        job=SimpleNamespace(id="job-new"),
        company_id=1,
        job_type="sim_cleanup",
        idempotency_key="key-1",
    )

    assert created is existing
    assert len(db.added) == 1


@pytest.mark.asyncio
async def test_insert_nested_or_get_existing_reraises_integrity_when_row_missing(
    monkeypatch,
):
    db = _NestedFailureDB()

    async def _load_none(*_args, **_kwargs):
        return None

    monkeypatch.setattr(create_get_repo, "load_idempotent_job", _load_none)

    with pytest.raises(IntegrityError):
        await create_get_repo._insert_nested_or_get_existing(
            db,
            job=SimpleNamespace(id="job-new"),
            company_id=1,
            job_type="sim_cleanup",
            idempotency_key="key-2",
        )
