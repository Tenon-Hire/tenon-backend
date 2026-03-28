from __future__ import annotations

import pytest

from tests.shared.jobs.repositories.shared_jobs_repository_utils import *


@pytest.mark.asyncio
async def test_create_or_update_idempotent_updates_existing_queued_job(async_session):
    company = await create_company(async_session, name="Jobs Co Update")
    now = datetime.now(UTC)

    first = await jobs_repo.create_or_update_idempotent(
        async_session,
        job_type="scenario_generation",
        idempotency_key="idem-update-queued",
        payload_json={"v": 1},
        company_id=company.id,
        candidate_session_id=None,
        correlation_id="corr-a",
        next_run_at=now + timedelta(minutes=30),
        commit=True,
    )
    second = await jobs_repo.create_or_update_idempotent(
        async_session,
        job_type="scenario_generation",
        idempotency_key="idem-update-queued",
        payload_json={"v": 2},
        company_id=company.id,
        candidate_session_id=None,
        correlation_id="corr-b",
        next_run_at=now + timedelta(hours=2),
        commit=True,
    )

    assert first.id == second.id
    refreshed = await jobs_repo.get_by_id(async_session, first.id)
    assert refreshed is not None
    assert refreshed.payload_json == {"v": 2}
    assert refreshed.correlation_id == "corr-b"
    expected_next_run = now + timedelta(hours=2)
    observed_next_run = refreshed.next_run_at
    assert observed_next_run is not None
    if observed_next_run.tzinfo is None:
        observed_next_run = observed_next_run.replace(tzinfo=UTC)
    assert observed_next_run == expected_next_run


@pytest.mark.asyncio
async def test_create_or_update_idempotent_keeps_existing_immutable_job_unchanged(
    async_session,
):
    company = await create_company(async_session, name="Jobs Co Immutable")
    now = datetime.now(UTC)
    first = await jobs_repo.create_or_update_idempotent(
        async_session,
        job_type="scenario_generation",
        idempotency_key="idem-update-immutable",
        payload_json={"v": 1},
        company_id=company.id,
        candidate_session_id=None,
        correlation_id="corr-a",
        next_run_at=now + timedelta(minutes=10),
        commit=True,
    )
    first.status = JOB_STATUS_SUCCEEDED
    await async_session.commit()

    second = await jobs_repo.create_or_update_idempotent(
        async_session,
        job_type="scenario_generation",
        idempotency_key="idem-update-immutable",
        payload_json={"v": 2},
        company_id=company.id,
        candidate_session_id=None,
        correlation_id="corr-b",
        next_run_at=now + timedelta(hours=1),
        commit=True,
    )

    assert first.id == second.id
    refreshed = await jobs_repo.get_by_id(async_session, first.id)
    assert refreshed is not None
    assert refreshed.status == JOB_STATUS_SUCCEEDED
    assert refreshed.payload_json == {"v": 1}
    assert refreshed.correlation_id == "corr-a"
