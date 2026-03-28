from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.candidates.candidate_sessions.repositories import (
    repository_day_audits as day_audit_repo,
)
from tests.candidates.repositories.candidates_day_audits_repository_utils import (
    create_existing_day_audit,
    cutoff_at_2026_03_10,
)


@pytest.mark.asyncio
async def test_create_day_audit_once_commit_true_handles_integrity_race(
    async_session,
    monkeypatch,
):
    candidate_session, existing, created = await create_existing_day_audit(
        async_session,
        day_index=2,
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
        cutoff_at=cutoff_at_2026_03_10(),
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
    candidate_session, existing, created = await create_existing_day_audit(
        async_session,
        day_index=3,
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
        cutoff_at=cutoff_at_2026_03_10(),
        cutoff_commit_sha="sha-race",
        eval_basis_ref="refs/heads/main@cutoff",
        commit=False,
    )
    assert raced_created is False
    assert raced.id == existing.id
    assert raced.cutoff_commit_sha == "sha-existing"
