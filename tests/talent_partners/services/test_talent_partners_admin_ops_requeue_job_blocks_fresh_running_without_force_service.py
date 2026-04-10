from __future__ import annotations

import pytest

from tests.talent_partners.services.talent_partners_admin_ops_utils import *


@pytest.mark.asyncio
async def test_requeue_job_blocks_fresh_running_without_force(
    async_session, monkeypatch
):
    talent_partner = await create_talent_partner(
        async_session, email="requeue-running-fresh-owner@test.com"
    )
    company = await async_session.get(Company, talent_partner.company_id)
    assert company is not None
    monkeypatch.setattr(settings, "DEMO_ADMIN_JOB_STALE_SECONDS", 900)

    job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_RUNNING,
        job_type="admin-requeue-running-fresh-unit",
    )
    job.locked_at = datetime.now(UTC)
    job.locked_by = "worker-fresh"
    await async_session.commit()

    with pytest.raises(ApiError) as excinfo:
        await admin_ops_service.requeue_job(
            async_session,
            actor=_actor(),
            job_id=job.id,
            reason="fresh running should block",
            force=False,
            now=datetime.now(UTC),
        )
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == admin_ops_service.UNSAFE_OPERATION_ERROR_CODE
    assert excinfo.value.details["status"] == JOB_STATUS_RUNNING
    assert excinfo.value.details["staleRunningThresholdSeconds"] == 900

    audits = (
        (
            await async_session.execute(
                select(AdminActionAudit).where(
                    AdminActionAudit.target_id == job.id,
                    AdminActionAudit.action == admin_ops_service.JOB_REQUEUE_ACTION,
                )
            )
        )
        .scalars()
        .all()
    )
    assert audits == []
