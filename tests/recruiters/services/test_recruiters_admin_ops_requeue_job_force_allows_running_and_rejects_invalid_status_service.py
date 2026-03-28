from __future__ import annotations

import pytest

from tests.recruiters.services.recruiters_admin_ops_utils import *


@pytest.mark.asyncio
async def test_requeue_job_force_allows_running_and_rejects_invalid_status(
    async_session, monkeypatch
):
    recruiter = await create_recruiter(
        async_session, email="requeue-running-force-owner@test.com"
    )
    company = await async_session.get(Company, recruiter.company_id)
    assert company is not None
    monkeypatch.setattr(settings, "DEMO_ADMIN_JOB_STALE_SECONDS", 0)

    running_job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_RUNNING,
        job_type="admin-requeue-running-force-unit",
    )
    running_job.locked_at = datetime.now(UTC)
    running_job.locked_by = "worker-force"

    blocked_job = await create_job(
        async_session,
        company=company,
        status="manual_hold",
        job_type="admin-requeue-manual-hold-unit",
    )
    await async_session.commit()

    forced = await admin_ops_service.requeue_job(
        async_session,
        actor=_actor(),
        job_id=running_job.id,
        reason="force running job requeue",
        force=True,
    )
    assert forced.new_status == JOB_STATUS_QUEUED

    forced_audit = await _audit_by_id(async_session, forced.audit_id)
    assert forced_audit.payload_json["staleRunningThresholdSeconds"] == 900

    with pytest.raises(ApiError) as excinfo:
        await admin_ops_service.requeue_job(
            async_session,
            actor=_actor(),
            job_id=blocked_job.id,
            reason="force blocked manual hold",
            force=True,
        )
    assert excinfo.value.status_code == 409
    assert excinfo.value.details["status"] == "manual_hold"
