from __future__ import annotations

import pytest

from app.shared.jobs.repositories import (
    shared_jobs_repositories_repository_create_update_many_repository as create_update_many_repo,
)
from tests.shared.jobs.repositories.shared_jobs_repository_utils import *


@pytest.mark.asyncio
async def test_create_or_update_many_idempotent_updates_and_creates(async_session):
    company = await create_company(async_session, name="Jobs Co Bulk Upsert")
    existing = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="day_close_finalize_text",
        idempotency_key="bulk-existing",
        payload_json={"taskId": 1},
        company_id=company.id,
    )

    jobs = await jobs_repo.create_or_update_many_idempotent(
        async_session,
        company_id=company.id,
        jobs=[
            jobs_repo.IdempotentJobSpec(
                job_type="day_close_finalize_text",
                idempotency_key="bulk-existing",
                payload_json={"taskId": 2},
                max_attempts=9,
                correlation_id="bulk-corr-1",
            ),
            jobs_repo.IdempotentJobSpec(
                job_type="day_close_enforcement",
                idempotency_key="bulk-new",
                payload_json={"dayIndex": 2},
                max_attempts=7,
                correlation_id="bulk-corr-2",
            ),
        ],
        commit=True,
    )

    assert len(jobs) == 2
    assert jobs[0].id == existing.id

    refreshed_existing = await jobs_repo.get_by_id(async_session, existing.id)
    assert refreshed_existing is not None
    assert refreshed_existing.payload_json == {"taskId": 2}
    assert refreshed_existing.max_attempts == 9
    assert refreshed_existing.correlation_id == "bulk-corr-1"

    created_new = await jobs_repo._load_idempotent_job(
        async_session,
        company_id=company.id,
        job_type="day_close_enforcement",
        idempotency_key="bulk-new",
    )
    assert created_new is not None
    assert created_new.payload_json == {"dayIndex": 2}
    assert created_new.max_attempts == 7
    assert created_new.correlation_id == "bulk-corr-2"


@pytest.mark.asyncio
async def test_create_or_update_many_idempotent_skips_updates_for_immutable_existing_job(
    async_session,
):
    company = await create_company(async_session, name="Jobs Co Bulk Immutable")
    existing = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="day_close_finalize_text",
        idempotency_key="bulk-immutable",
        payload_json={"taskId": 1},
        company_id=company.id,
    )
    existing.status = JOB_STATUS_SUCCEEDED
    await async_session.commit()

    jobs = await jobs_repo.create_or_update_many_idempotent(
        async_session,
        company_id=company.id,
        jobs=[
            jobs_repo.IdempotentJobSpec(
                job_type="day_close_finalize_text",
                idempotency_key="bulk-immutable",
                payload_json={"taskId": 999},
            )
        ],
        commit=True,
    )

    assert len(jobs) == 1
    refreshed = await jobs_repo.get_by_id(async_session, existing.id)
    assert refreshed is not None
    assert refreshed.status == JOB_STATUS_SUCCEEDED
    assert refreshed.payload_json == {"taskId": 1}


def test_resolve_jobs_in_order_skips_specs_missing_from_map():
    specs = [
        jobs_repo.IdempotentJobSpec(
            job_type="day_close_finalize_text",
            idempotency_key="resolve-missing-1",
            payload_json={"x": 1},
        ),
        jobs_repo.IdempotentJobSpec(
            job_type="day_close_enforcement",
            idempotency_key="resolve-missing-2",
            payload_json={"x": 2},
        ),
    ]

    assert create_update_many_repo._resolve_jobs_in_order(specs, existing_map={}) == []
