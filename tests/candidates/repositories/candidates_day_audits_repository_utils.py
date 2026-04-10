from __future__ import annotations

from datetime import UTC, datetime

from app.candidates.candidate_sessions.repositories import (
    repository_day_audits as day_audit_repo,
)
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


def cutoff_at_2026_03_10() -> datetime:
    return datetime(2026, 3, 10, 21, 0, tzinfo=UTC)


async def seed_candidate_session(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="day-audit-repo@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="in_progress",
    )
    await async_session.commit()
    return candidate_session


async def create_existing_day_audit(async_session, *, day_index: int):
    candidate_session = await seed_candidate_session(async_session)
    existing, created = await day_audit_repo.create_day_audit_once(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=day_index,
        cutoff_at=cutoff_at_2026_03_10(),
        cutoff_commit_sha="sha-existing",
        eval_basis_ref="refs/heads/main@cutoff",
        commit=True,
    )
    return candidate_session, existing, created
