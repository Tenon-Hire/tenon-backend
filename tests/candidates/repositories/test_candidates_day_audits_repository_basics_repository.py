from __future__ import annotations

import pytest

from app.candidates.candidate_sessions.repositories import (
    repository_day_audits as day_audit_repo,
)
from tests.candidates.repositories.candidates_day_audits_repository_utils import (
    cutoff_at_2026_03_10,
    seed_candidate_session,
)


@pytest.mark.asyncio
async def test_list_day_audits_handles_empty_inputs(async_session):
    assert (
        await day_audit_repo.list_day_audits(async_session, candidate_session_ids=[])
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
    candidate_session = await seed_candidate_session(async_session)
    day_audit, created = await day_audit_repo.create_day_audit_once(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
        cutoff_at=cutoff_at_2026_03_10(),
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
    candidate_session = await seed_candidate_session(async_session)
    first, first_created = await day_audit_repo.create_day_audit_once(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
        cutoff_at=cutoff_at_2026_03_10(),
        cutoff_commit_sha="sha-1",
        eval_basis_ref="refs/heads/main@cutoff",
        commit=True,
    )
    assert first_created is True

    second, second_created = await day_audit_repo.create_day_audit_once(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
        cutoff_at=cutoff_at_2026_03_10(),
        cutoff_commit_sha="sha-2",
        eval_basis_ref="refs/heads/main@cutoff",
        commit=True,
    )
    assert second_created is False
    assert second.id == first.id
    assert second.cutoff_commit_sha == "sha-1"


@pytest.mark.asyncio
async def test_list_day_audits_without_day_indexes_returns_rows(async_session):
    candidate_session = await seed_candidate_session(async_session)
    await day_audit_repo.create_day_audit_once(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
        cutoff_at=cutoff_at_2026_03_10(),
        cutoff_commit_sha="sha-4",
        eval_basis_ref="refs/heads/main@cutoff",
        commit=True,
    )

    listed = await day_audit_repo.list_day_audits(
        async_session,
        candidate_session_ids=[candidate_session.id],
    )

    assert len(listed) == 1
    assert listed[0].day_index == 2
