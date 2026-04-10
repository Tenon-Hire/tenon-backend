from __future__ import annotations

import pytest

from tests.talent_partners.routes.talent_partners_admin_demo_ops_utils import *


@pytest.mark.asyncio
async def test_requeue_running_job_requires_force_if_not_stale(
    async_client,
    async_session,
    monkeypatch,
):
    admin_email = "ops-requeue-force@test.com"
    _enable_demo_mode(monkeypatch, allowlist_emails=[admin_email])

    talent_partner = await create_talent_partner(
        async_session, email="owner-requeue-force@test.com"
    )
    company = await async_session.get(Company, talent_partner.company_id)
    assert company is not None
    job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_RUNNING,
        job_type="running_force_job",
        next_run_at=datetime.now(UTC),
    )
    job.locked_at = datetime.now(UTC)
    job.locked_by = "worker-1"
    await async_session.commit()

    blocked = await async_client.post(
        f"/api/admin/jobs/{job.id}/requeue",
        json={"reason": "Should block while fresh running", "force": False},
        headers=_admin_headers(admin_email),
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["errorCode"] == "UNSAFE_OPERATION"

    forced = await async_client.post(
        f"/api/admin/jobs/{job.id}/requeue",
        json={"reason": "Force requeue during demo", "force": True},
        headers=_admin_headers(admin_email),
    )
    assert forced.status_code == 200, forced.text
    assert forced.json()["newStatus"] == JOB_STATUS_QUEUED
