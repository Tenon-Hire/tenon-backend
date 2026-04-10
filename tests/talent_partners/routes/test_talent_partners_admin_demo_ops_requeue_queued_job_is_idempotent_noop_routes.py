from __future__ import annotations

import pytest

from tests.talent_partners.routes.talent_partners_admin_demo_ops_utils import *


@pytest.mark.asyncio
async def test_requeue_queued_job_is_idempotent_noop(
    async_client,
    async_session,
    monkeypatch,
):
    admin_email = "ops-requeue-noop@test.com"
    _enable_demo_mode(monkeypatch, allowlist_emails=[admin_email])

    talent_partner = await create_talent_partner(
        async_session, email="owner-requeue-noop@test.com"
    )
    company = await async_session.get(Company, talent_partner.company_id)
    assert company is not None
    job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_QUEUED,
        job_type="noop_requeue_job",
    )
    await async_session.commit()

    first = await async_client.post(
        f"/api/admin/jobs/{job.id}/requeue",
        json={"reason": "No-op check one", "force": False},
        headers=_admin_headers(admin_email),
    )
    assert first.status_code == 200, first.text
    assert first.json()["previousStatus"] == JOB_STATUS_QUEUED
    assert first.json()["newStatus"] == JOB_STATUS_QUEUED

    second = await async_client.post(
        f"/api/admin/jobs/{job.id}/requeue",
        json={"reason": "No-op check two", "force": False},
        headers=_admin_headers(admin_email),
    )
    assert second.status_code == 200, second.text
    assert second.json()["previousStatus"] == JOB_STATUS_QUEUED
    assert second.json()["newStatus"] == JOB_STATUS_QUEUED

    refreshed_job = await async_session.get(type(job), job.id)
    assert refreshed_job is not None
    assert refreshed_job.status == JOB_STATUS_QUEUED
