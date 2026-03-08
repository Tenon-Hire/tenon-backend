from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.repositories.candidate_sessions import repository_day_audits as day_audit_repo
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
)


async def _seed_candidate_session(async_session):
    recruiter = await create_recruiter(async_session, email="day-audit-repo@test.com")
    simulation, _tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="in_progress",
    )
    await async_session.commit()
    return candidate_session


@pytest.mark.asyncio
async def test_list_day_audits_handles_empty_inputs(async_session):
    assert (
        await day_audit_repo.list_day_audits(
            async_session,
            candidate_session_ids=[],
        )
        == []
    )
    assert (
        await day_audit_repo.list_day_audits(
            async_session,
            candidate_session_ids=[1],
            day_indexes=[],
        )
        == []
    )


@pytest.mark.asyncio
async def test_create_day_audit_once_commit_false_and_list(async_session):
    candidate_session = await _seed_candidate_session(async_session)
    cutoff_at = datetime(2026, 3, 10, 21, 0, tzinfo=UTC)

    day_audit, created = await day_audit_repo.create_day_audit_once(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
        cutoff_at=cutoff_at,
        cutoff_commit_sha="sha-1",
        eval_basis_ref="refs/heads/main@cutoff",
        commit=False,
    )
    assert created is True
    await async_session.commit()

    fetched = await day_audit_repo.get_day_audit(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
    )
    assert fetched is not None
    assert fetched.id == day_audit.id

    listed = await day_audit_repo.list_day_audits(
        async_session,
        candidate_session_ids=[candidate_session.id],
        day_indexes=[2],
    )
    assert len(listed) == 1
    assert listed[0].cutoff_commit_sha == "sha-1"


@pytest.mark.asyncio
async def test_create_day_audit_once_returns_existing_when_already_present(
    async_session,
):
    candidate_session = await _seed_candidate_session(async_session)
    cutoff_at = datetime(2026, 3, 10, 21, 0, tzinfo=UTC)
    first, first_created = await day_audit_repo.create_day_audit_once(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
        cutoff_at=cutoff_at,
        cutoff_commit_sha="sha-1",
        eval_basis_ref="refs/heads/main@cutoff",
        commit=True,
    )
    assert first_created is True

    second, second_created = await day_audit_repo.create_day_audit_once(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
        cutoff_at=cutoff_at,
        cutoff_commit_sha="sha-2",
        eval_basis_ref="refs/heads/main@cutoff",
        commit=True,
    )
    assert second_created is False
    assert second.id == first.id
    assert second.cutoff_commit_sha == "sha-1"


@pytest.mark.asyncio
async def test_create_day_audit_once_commit_true_handles_integrity_race(
    async_session,
    monkeypatch,
):
    candidate_session = await _seed_candidate_session(async_session)
    cutoff_at = datetime(2026, 3, 10, 21, 0, tzinfo=UTC)
    existing, created = await day_audit_repo.create_day_audit_once(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
        cutoff_at=cutoff_at,
        cutoff_commit_sha="sha-existing",
        eval_basis_ref="refs/heads/main@cutoff",
        commit=True,
    )
    assert created is True

    original_get_day_audit = day_audit_repo.get_day_audit
    call_count = {"n": 0}

    async def _fake_get_day_audit(_db, *, candidate_session_id, day_index):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return None
        return await original_get_day_audit(
            _db,
            candidate_session_id=candidate_session_id,
            day_index=day_index,
        )

    async def _fake_commit():
        raise IntegrityError("insert", {}, Exception("race"))

    monkeypatch.setattr(day_audit_repo, "get_day_audit", _fake_get_day_audit)
    monkeypatch.setattr(async_session, "commit", _fake_commit)
    raced, raced_created = await day_audit_repo.create_day_audit_once(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
        cutoff_at=cutoff_at,
        cutoff_commit_sha="sha-race",
        eval_basis_ref="refs/heads/main@cutoff",
        commit=True,
    )
    assert raced_created is False
    assert raced.id == existing.id
    assert raced.cutoff_commit_sha == "sha-existing"


@pytest.mark.asyncio
async def test_create_day_audit_once_commit_false_handles_integrity_race(
    async_session,
    monkeypatch,
):
    candidate_session = await _seed_candidate_session(async_session)
    cutoff_at = datetime(2026, 3, 10, 21, 0, tzinfo=UTC)
    existing, created = await day_audit_repo.create_day_audit_once(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=3,
        cutoff_at=cutoff_at,
        cutoff_commit_sha="sha-existing",
        eval_basis_ref="refs/heads/main@cutoff",
        commit=True,
    )
    assert created is True

    original_get_day_audit = day_audit_repo.get_day_audit
    call_count = {"n": 0}

    async def _fake_get_day_audit(_db, *, candidate_session_id, day_index):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return None
        return await original_get_day_audit(
            _db,
            candidate_session_id=candidate_session_id,
            day_index=day_index,
        )

    async def _fake_flush():
        raise IntegrityError("insert", {}, Exception("race"))

    monkeypatch.setattr(day_audit_repo, "get_day_audit", _fake_get_day_audit)
    monkeypatch.setattr(async_session, "flush", _fake_flush)
    raced, raced_created = await day_audit_repo.create_day_audit_once(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=3,
        cutoff_at=cutoff_at,
        cutoff_commit_sha="sha-race",
        eval_basis_ref="refs/heads/main@cutoff",
        commit=False,
    )
    assert raced_created is False
    assert raced.id == existing.id
    assert raced.cutoff_commit_sha == "sha-existing"


@pytest.mark.asyncio
async def test_create_day_audit_once_commit_true_raises_when_integrity_without_existing(
    async_session,
    monkeypatch,
):
    candidate_session = await _seed_candidate_session(async_session)
    cutoff_at = datetime(2026, 3, 10, 21, 0, tzinfo=UTC)

    async def _fake_get_day_audit(_db, *, candidate_session_id, day_index):
        return None

    async def _fake_commit():
        raise IntegrityError("insert", {}, Exception("race"))

    monkeypatch.setattr(day_audit_repo, "get_day_audit", _fake_get_day_audit)
    monkeypatch.setattr(async_session, "commit", _fake_commit)

    with pytest.raises(IntegrityError):
        await day_audit_repo.create_day_audit_once(
            async_session,
            candidate_session_id=candidate_session.id,
            day_index=2,
            cutoff_at=cutoff_at,
            cutoff_commit_sha="sha-race",
            eval_basis_ref="refs/heads/main@cutoff",
            commit=True,
        )


@pytest.mark.asyncio
async def test_create_day_audit_once_commit_false_raises_when_integrity_without_existing(
    async_session,
    monkeypatch,
):
    candidate_session = await _seed_candidate_session(async_session)
    cutoff_at = datetime(2026, 3, 10, 21, 0, tzinfo=UTC)

    async def _fake_get_day_audit(_db, *, candidate_session_id, day_index):
        return None

    async def _fake_flush():
        raise IntegrityError("insert", {}, Exception("race"))

    monkeypatch.setattr(day_audit_repo, "get_day_audit", _fake_get_day_audit)
    monkeypatch.setattr(async_session, "flush", _fake_flush)

    with pytest.raises(IntegrityError):
        await day_audit_repo.create_day_audit_once(
            async_session,
            candidate_session_id=candidate_session.id,
            day_index=3,
            cutoff_at=cutoff_at,
            cutoff_commit_sha="sha-race",
            eval_basis_ref="refs/heads/main@cutoff",
            commit=False,
        )
