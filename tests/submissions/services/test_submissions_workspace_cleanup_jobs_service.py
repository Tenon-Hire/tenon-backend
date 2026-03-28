from __future__ import annotations

import pytest

from app.submissions.services import (
    submissions_services_submissions_workspace_cleanup_jobs_service as cleanup_jobs,
)
from tests.shared.factories import create_company


def test_workspace_cleanup_idempotency_key_requires_run_key():
    with pytest.raises(ValueError, match="run_key is required"):
        cleanup_jobs.workspace_cleanup_idempotency_key(1, run_key=" ")


@pytest.mark.asyncio
async def test_enqueue_workspace_cleanup_job_is_idempotent(async_session):
    company = await create_company(async_session, name="Workspace Cleanup Co")

    first = await cleanup_jobs.enqueue_workspace_cleanup_job(
        async_session,
        company_id=company.id,
        run_key="manual-run",
        commit=True,
    )
    second = await cleanup_jobs.enqueue_workspace_cleanup_job(
        async_session,
        company_id=company.id,
        run_key="manual-run",
        commit=True,
    )

    assert first.id == second.id
    assert first.job_type == cleanup_jobs.WORKSPACE_CLEANUP_JOB_TYPE
    assert first.idempotency_key == (f"workspace_cleanup:{company.id}:manual-run")
    assert first.payload_json == {"companyId": company.id, "runKey": "manual-run"}
