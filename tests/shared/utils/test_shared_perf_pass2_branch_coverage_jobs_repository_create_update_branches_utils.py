from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_jobs_repository_create_update_branches(async_session):
    company = await create_company(async_session, name="Jobs Branch Co")
    company_id = company.id
    await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="branch_job",
        idempotency_key="branch-key",
        payload_json={"a": 1},
        company_id=company_id,
    )

    updated = await jobs_repo.create_or_update_idempotent(
        async_session,
        job_type="branch_job",
        idempotency_key="branch-key",
        payload_json={"a": 4},
        company_id=company_id,
        commit=False,
    )
    assert updated.payload_json == {"a": 4}

    created = await jobs_repo.create_or_update_idempotent(
        async_session,
        job_type="branch_new",
        idempotency_key="branch-new-key",
        payload_json={"b": 1},
        company_id=company_id,
        commit=False,
    )
    assert created.job_type == "branch_new"
    assert created.idempotency_key == "branch-new-key"

    resolved = await jobs_repo.create_or_update_many_idempotent(
        async_session,
        company_id=company_id,
        jobs=[],
        commit=False,
    )
    assert resolved == []
