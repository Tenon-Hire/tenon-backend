from __future__ import annotations

import pytest

from tests.shared.jobs.repositories.shared_jobs_repository_utils import *


@pytest.mark.asyncio
async def test_claim_next_runnable_never_reclaims_terminal_state_jobs(async_session):
    company = await create_company(async_session, name="Jobs Co Terminal")
    old_lock = datetime.now(UTC) - timedelta(hours=4)
    succeeded = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_SUCCEEDED,
        attempt=3,
        max_attempts=5,
        next_run_at=None,
    )
    succeeded.locked_at = old_lock
    succeeded.locked_by = "old-worker-succeeded"

    dead_letter = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_DEAD_LETTER,
        attempt=5,
        max_attempts=5,
        next_run_at=None,
    )
    dead_letter.locked_at = old_lock
    dead_letter.locked_by = "old-worker-dead-letter"
    await async_session.commit()

    claimed = await jobs_repo.claim_next_runnable(
        async_session,
        worker_id="fresh-worker",
        now=datetime.now(UTC),
        lease_seconds=300,
    )
    assert claimed is None

    refreshed_succeeded = await jobs_repo.get_by_id(async_session, succeeded.id)
    refreshed_dead_letter = await jobs_repo.get_by_id(async_session, dead_letter.id)
    assert refreshed_succeeded is not None
    assert refreshed_dead_letter is not None
    assert refreshed_succeeded.status == JOB_STATUS_SUCCEEDED
    assert refreshed_dead_letter.status == JOB_STATUS_DEAD_LETTER
