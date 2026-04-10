from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.submissions.repositories import repository as submissions_repo_impl
from app.submissions.repositories import (
    submissions_repositories_submissions_core_repository as submissions_repo,
)
from tests.shared.factories import (
    create_candidate_session,
    create_submission,
    create_talent_partner,
    create_trial,
)


@pytest.mark.asyncio
async def test_find_duplicate_false(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="dupfalse@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim)
    dup = await submissions_repo.find_duplicate(async_session, cs.id, tasks[0].id)
    assert dup is False


@pytest.mark.asyncio
async def test_find_duplicate_true(async_session):
    talent_partner = await create_talent_partner(async_session, email="duptru@test.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim)
    await create_submission(async_session, candidate_session=cs, task=tasks[0])
    dup = await submissions_repo.find_duplicate(async_session, cs.id, tasks[0].id)
    assert dup is True


@pytest.mark.asyncio
async def test_create_handoff_submission_flush_path(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="handoff-flush@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim)
    task = tasks[0]

    created = await submissions_repo_impl.create_handoff_submission(
        async_session,
        candidate_session_id=cs.id,
        task_id=task.id,
        recording_id=123,
        submitted_at=datetime.now(UTC),
        commit=False,
    )

    assert created.id is not None
    assert created.recording_id == 123


class _FakeScalarResult:
    def __init__(self, value: int):
        self._value = value

    def scalar_one(self) -> int:
        return self._value


class _FakeBind:
    def __init__(self, dialect_name: str):
        self.dialect = SimpleNamespace(name=dialect_name)


class _FakeDB:
    def __init__(self, dialect_name: str, scalar_value: int = 0):
        self._bind = _FakeBind(dialect_name)
        self.scalar_value = scalar_value
        self.executed_stmt = None
        self.flush_calls = 0

    def get_bind(self):
        return self._bind

    async def execute(self, stmt):
        self.executed_stmt = stmt
        return _FakeScalarResult(self.scalar_value)

    async def flush(self):
        self.flush_calls += 1


@pytest.mark.asyncio
async def test_upsert_handoff_submission_postgresql_branch_uses_returning_id():
    db = _FakeDB("postgresql", scalar_value=77)

    result = await submissions_repo_impl.upsert_handoff_submission(
        db,
        candidate_session_id=1,
        task_id=2,
        recording_id=3,
        submitted_at=datetime.now(UTC),
    )

    assert result == 77
    assert db.executed_stmt is not None


@pytest.mark.asyncio
async def test_upsert_handoff_submission_fallback_updates_existing(monkeypatch):
    db = _FakeDB("mysql")
    existing = SimpleNamespace(id=42, recording_id=1, submitted_at=None)

    async def _get_existing(*_args, **_kwargs):
        return existing

    monkeypatch.setattr(
        submissions_repo_impl, "get_by_candidate_session_task", _get_existing
    )

    result = await submissions_repo_impl.upsert_handoff_submission(
        db,
        candidate_session_id=10,
        task_id=20,
        recording_id=30,
        submitted_at=datetime(2026, 3, 20, tzinfo=UTC),
    )

    assert result == 42
    assert existing.recording_id == 30
    assert existing.submitted_at == datetime(2026, 3, 20, tzinfo=UTC)
    assert db.flush_calls == 1


@pytest.mark.asyncio
async def test_upsert_handoff_submission_fallback_creates_when_missing(monkeypatch):
    db = _FakeDB("mysql")

    async def _missing(*_args, **_kwargs):
        return None

    async def _create(*_args, **kwargs):
        assert kwargs["commit"] is False
        return SimpleNamespace(id=55)

    monkeypatch.setattr(
        submissions_repo_impl, "get_by_candidate_session_task", _missing
    )
    monkeypatch.setattr(submissions_repo_impl, "create_handoff_submission", _create)

    result = await submissions_repo_impl.upsert_handoff_submission(
        db,
        candidate_session_id=10,
        task_id=20,
        recording_id=30,
        submitted_at=datetime.now(UTC),
    )

    assert result == 55
