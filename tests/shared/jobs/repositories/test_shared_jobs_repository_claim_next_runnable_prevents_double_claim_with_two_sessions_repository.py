from __future__ import annotations

import pytest

from tests.shared.jobs.repositories.shared_jobs_repository_utils import *


@pytest.mark.asyncio
async def test_claim_next_runnable_prevents_double_claim_with_two_sessions(
    async_session,
):
    company = await create_company(async_session, name="Jobs Co Double Claim")
    job = await create_job(
        async_session,
        company=company,
        status="queued",
        attempt=0,
        next_run_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    await async_session.commit()

    session_maker = _session_maker(async_session)
    now = datetime.now(UTC)
    async with session_maker() as session_a, session_maker() as session_b:
        claimed_a, claimed_b = await asyncio.gather(
            jobs_repo.claim_next_runnable(
                session_a,
                worker_id="worker-a",
                now=now,
                lease_seconds=300,
            ),
            jobs_repo.claim_next_runnable(
                session_b,
                worker_id="worker-b",
                now=now,
                lease_seconds=300,
            ),
        )

    claimed = [job_row for job_row in [claimed_a, claimed_b] if job_row is not None]
    assert len(claimed) == 1
    winning_claim = claimed[0]
    assert winning_claim.id == job.id
    assert winning_claim.status == JOB_STATUS_RUNNING
    assert winning_claim.attempt == 1
    assert winning_claim.locked_by in {"worker-a", "worker-b"}

    refreshed = await jobs_repo.get_by_id(async_session, job.id)
    assert refreshed is not None
    assert refreshed.status == JOB_STATUS_RUNNING
    assert refreshed.locked_by == winning_claim.locked_by
