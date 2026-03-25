from __future__ import annotations

import pytest

from tests.shared.jobs.repositories.shared_jobs_repository_utils import *


@pytest.mark.asyncio
async def test_claim_next_runnable_reclaims_stale_running_job(async_session):
    company = await create_company(async_session, name="Jobs Co 3")
    stale_time = datetime.now(UTC) - timedelta(minutes=20)
    running_job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_RUNNING,
        attempt=1,
        next_run_at=None,
    )
    running_job.locked_at = stale_time
    await async_session.commit()

    claimed = await jobs_repo.claim_next_runnable(
        async_session,
        worker_id="w1",
        now=datetime.now(UTC),
        lease_seconds=300,
    )
    assert claimed is not None
    assert claimed.id == running_job.id
    assert claimed.status == JOB_STATUS_RUNNING
    assert claimed.attempt == 2
    assert claimed.locked_by == "w1"
