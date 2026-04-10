from __future__ import annotations

import pytest

from tests.talent_partners.services.talent_partners_admin_ops_utils import *


@pytest.mark.asyncio
async def test_requeue_job_stale_running_paths(async_session, monkeypatch):
    talent_partner = await create_talent_partner(
        async_session, email="requeue-running-stale-owner@test.com"
    )
    company = await async_session.get(Company, talent_partner.company_id)
    assert company is not None
    monkeypatch.setattr(settings, "DEMO_ADMIN_JOB_STALE_SECONDS", 60)

    now = datetime.now(UTC).replace(microsecond=0)
    stale_job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_RUNNING,
        job_type="admin-requeue-running-stale-unit",
    )
    stale_job.locked_at = now - timedelta(seconds=180)
    stale_job.locked_by = "worker-stale"

    missing_lock_job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_RUNNING,
        job_type="admin-requeue-running-no-lock-unit",
    )
    missing_lock_job.locked_at = None
    missing_lock_job.locked_by = "worker-no-lock"
    await async_session.commit()

    stale_result = await admin_ops_service.requeue_job(
        async_session,
        actor=_actor(),
        job_id=stale_job.id,
        reason="stale running requeue",
        force=False,
        now=now,
    )
    stale_audit = await _audit_by_id(async_session, stale_result.audit_id)
    assert stale_audit.payload_json["staleRunning"] is True
    assert stale_audit.payload_json["staleRunningThresholdSeconds"] == 60

    no_lock_result = await admin_ops_service.requeue_job(
        async_session,
        actor=_actor(),
        job_id=missing_lock_job.id,
        reason="requeue running without lock",
        force=False,
        now=now,
    )
    no_lock_audit = await _audit_by_id(async_session, no_lock_result.audit_id)
    assert no_lock_audit.payload_json["staleRunning"] is True
