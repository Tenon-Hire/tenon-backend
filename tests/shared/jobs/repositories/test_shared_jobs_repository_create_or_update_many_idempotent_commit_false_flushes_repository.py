from __future__ import annotations

import pytest

from tests.shared.jobs.repositories.shared_jobs_repository_utils import *


@pytest.mark.asyncio
async def test_create_or_update_many_idempotent_commit_false_flushes(async_session):
    company = await create_company(async_session, name="Jobs Co Bulk Flush")

    jobs = await jobs_repo.create_or_update_many_idempotent(
        async_session,
        company_id=company.id,
        jobs=[
            jobs_repo.IdempotentJobSpec(
                job_type="day_close_finalize_text",
                idempotency_key="bulk-flush-1",
                payload_json={"taskId": 5},
            ),
            jobs_repo.IdempotentJobSpec(
                job_type="day_close_enforcement",
                idempotency_key="bulk-flush-2",
                payload_json={"taskId": 8},
            ),
        ],
        commit=False,
    )
    assert len(jobs) == 2

    await async_session.commit()
    persisted = await jobs_repo._load_idempotent_job(
        async_session,
        company_id=company.id,
        job_type="day_close_enforcement",
        idempotency_key="bulk-flush-2",
    )
    assert persisted is not None
    assert persisted.payload_json == {"taskId": 8}
