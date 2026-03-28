from __future__ import annotations

import pytest

from tests.shared.jobs.repositories.shared_jobs_repository_utils import *


@pytest.mark.asyncio
async def test_requeue_nonterminal_idempotent_job_validates_and_flushes(async_session):
    company = await create_company(async_session, name="Jobs Co Requeue")
    now = datetime.now(UTC)
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="scenario_generation",
        idempotency_key="idem-requeue",
        payload_json={"windowEndAt": "2026-03-10T18:30:00Z"},
        company_id=company.id,
        next_run_at=now + timedelta(minutes=10),
    )

    with pytest.raises(ValueError):
        await jobs_repo.requeue_nonterminal_idempotent_job(
            async_session,
            company_id=company.id,
            job_type=" ",
            idempotency_key=job.idempotency_key,
            next_run_at=now + timedelta(hours=1),
            now=now,
        )
    with pytest.raises(ValueError):
        await jobs_repo.requeue_nonterminal_idempotent_job(
            async_session,
            company_id=company.id,
            job_type=job.job_type,
            idempotency_key=" ",
            next_run_at=now + timedelta(hours=1),
            now=now,
        )

    updated = await jobs_repo.requeue_nonterminal_idempotent_job(
        async_session,
        company_id=company.id,
        job_type=job.job_type,
        idempotency_key=job.idempotency_key,
        next_run_at=now + timedelta(hours=3),
        now=now,
        payload_json={"windowEndAt": "2026-03-10T21:30:00Z"},
        commit=False,
    )
    assert updated is not None
    assert updated.status == JOB_STATUS_QUEUED
    assert updated.payload_json == {"windowEndAt": "2026-03-10T21:30:00Z"}
    observed_next_run = updated.next_run_at
    assert observed_next_run is not None
    if observed_next_run.tzinfo is None:
        observed_next_run = observed_next_run.replace(tzinfo=UTC)
    assert observed_next_run == now + timedelta(hours=3)


@pytest.mark.asyncio
async def test_requeue_nonterminal_idempotent_job_preserves_payload_when_not_provided(
    async_session,
):
    company = await create_company(
        async_session, name="Jobs Co Requeue Existing Payload"
    )
    now = datetime.now(UTC)
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="scenario_generation",
        idempotency_key="idem-requeue-no-payload",
        payload_json={"windowEndAt": "2026-03-10T18:30:00Z"},
        company_id=company.id,
        next_run_at=now + timedelta(minutes=10),
    )

    updated = await jobs_repo.requeue_nonterminal_idempotent_job(
        async_session,
        company_id=company.id,
        job_type=job.job_type,
        idempotency_key=job.idempotency_key,
        next_run_at=now + timedelta(hours=2),
        now=now,
        payload_json=None,
        commit=False,
    )

    assert updated is not None
    assert updated.payload_json == {"windowEndAt": "2026-03-10T18:30:00Z"}
