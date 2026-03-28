from __future__ import annotations

import pytest

from tests.shared.jobs.repositories.shared_jobs_repository_utils import *


@pytest.mark.asyncio
async def test_create_or_get_idempotent_returns_existing(async_session):
    company = await create_company(async_session, name="Jobs Co")

    first = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="scenario_generation",
        idempotency_key="idem-1",
        payload_json={"a": 1},
        company_id=company.id,
    )
    second = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="scenario_generation",
        idempotency_key="idem-1",
        payload_json={"a": 2},
        company_id=company.id,
    )

    assert first.id == second.id
    fetched = await jobs_repo.get_by_id(async_session, first.id)
    assert fetched is not None
    assert fetched.id == first.id
