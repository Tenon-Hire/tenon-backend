from __future__ import annotations

import pytest

from tests.shared.jobs.repositories.shared_jobs_repository_utils import *


@pytest.mark.asyncio
async def test_create_or_get_idempotent_validates_payload_and_inputs(async_session):
    company = await create_company(async_session, name="Jobs Co 2")
    with pytest.raises(ValueError):
        await jobs_repo.create_or_get_idempotent(
            async_session,
            job_type=" ",
            idempotency_key="idem-2",
            payload_json={"ok": True},
            company_id=company.id,
        )
    with pytest.raises(ValueError):
        await jobs_repo.create_or_get_idempotent(
            async_session,
            job_type="x",
            idempotency_key=" ",
            payload_json={"ok": True},
            company_id=company.id,
        )
    with pytest.raises(ValueError):
        await jobs_repo.create_or_get_idempotent(
            async_session,
            job_type="x",
            idempotency_key="idem-2",
            payload_json={"ok": True},
            company_id=company.id,
            max_attempts=0,
        )
    with pytest.raises(ValueError):
        await jobs_repo.create_or_get_idempotent(
            async_session,
            job_type="x",
            idempotency_key="idem-3",
            payload_json={"blob": "x" * (jobs_repo.MAX_JOB_PAYLOAD_BYTES + 1)},
            company_id=company.id,
        )
