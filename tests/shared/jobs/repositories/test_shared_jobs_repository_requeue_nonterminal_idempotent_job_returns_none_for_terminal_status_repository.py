from __future__ import annotations

import pytest

from tests.shared.jobs.repositories.shared_jobs_repository_utils import *


@pytest.mark.asyncio
async def test_requeue_nonterminal_idempotent_job_returns_none_for_terminal_status(
    async_session,
):
    company = await create_company(async_session, name="Jobs Co Terminal Requeue")
    now = datetime.now(UTC)
    job = await create_job(
        async_session,
        company=company,
        job_type="scenario_generation",
        status=JOB_STATUS_SUCCEEDED,
        idempotency_key="idem-terminal-requeue",
        payload_json={"windowEndAt": "2026-03-10T18:30:00Z"},
        next_run_at=None,
    )
    await async_session.commit()

    before = await jobs_repo.get_by_id(async_session, job.id)
    assert before is not None

    updated = await jobs_repo.requeue_nonterminal_idempotent_job(
        async_session,
        company_id=company.id,
        job_type=job.job_type,
        idempotency_key=job.idempotency_key,
        next_run_at=now + timedelta(hours=3),
        now=now,
        payload_json={"windowEndAt": "2026-03-10T21:30:00Z"},
    )

    assert updated is None

    after = await jobs_repo.get_by_id(async_session, job.id)
    assert after is not None
    assert after.status == JOB_STATUS_SUCCEEDED
    assert after.payload_json == before.payload_json
    assert after.next_run_at == before.next_run_at
    assert after.last_error == before.last_error
