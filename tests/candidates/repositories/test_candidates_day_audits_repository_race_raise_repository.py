from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.candidates.candidate_sessions.repositories import (
    repository_day_audits as day_audit_repo,
)
from tests.candidates.repositories.candidates_day_audits_repository_utils import (
    cutoff_at_2026_03_10,
    seed_candidate_session,
)


@pytest.mark.asyncio
async def test_create_day_audit_once_commit_true_raises_when_integrity_without_existing(
    async_session,
    monkeypatch,
):
    candidate_session = await seed_candidate_session(async_session)

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
            cutoff_at=cutoff_at_2026_03_10(),
            cutoff_commit_sha="sha-race",
            eval_basis_ref="refs/heads/main@cutoff",
            commit=True,
        )


@pytest.mark.asyncio
async def test_create_day_audit_once_commit_false_raises_when_integrity_without_existing(
    async_session,
    monkeypatch,
):
    candidate_session = await seed_candidate_session(async_session)

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
            cutoff_at=cutoff_at_2026_03_10(),
            cutoff_commit_sha="sha-race",
            eval_basis_ref="refs/heads/main@cutoff",
            commit=False,
        )
