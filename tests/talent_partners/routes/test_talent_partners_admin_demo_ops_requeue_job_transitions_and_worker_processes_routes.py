from __future__ import annotations

import pytest

from tests.talent_partners.routes.talent_partners_admin_demo_ops_utils import *


@pytest.mark.asyncio
async def test_requeue_job_transitions_and_worker_processes(
    async_client,
    async_session,
    monkeypatch,
):
    admin_email = "ops-requeue@test.com"
    _enable_demo_mode(monkeypatch, allowlist_emails=[admin_email])

    talent_partner = await create_talent_partner(
        async_session, email="owner-requeue@test.com"
    )
    company = await async_session.get(Company, talent_partner.company_id)
    assert company is not None
    job = await create_job(
        async_session,
        company=company,
        job_type="admin_requeue_integration_job",
        status=JOB_STATUS_DEAD_LETTER,
        last_error="failed before demo",
        payload_json={"ok": True},
    )
    job_id = job.id
    await async_session.commit()

    response = await async_client.post(
        f"/api/admin/jobs/{job_id}/requeue",
        json={"reason": "Retry dead-lettered demo job", "force": False},
        headers=_admin_headers(admin_email),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["jobId"] == job_id
    assert body["previousStatus"] == JOB_STATUS_DEAD_LETTER
    assert body["newStatus"] == JOB_STATUS_QUEUED
    assert isinstance(body["auditId"], str)

    session_maker = _session_maker(async_session)
    worker.clear_handlers()
    try:
        worker.register_handler(
            "admin_requeue_integration_job", lambda _payload: {"ok": True}
        )
        handled = await worker.run_once(
            session_maker=session_maker,
            worker_id="admin-demo-ops-test-worker",
            now=datetime.now(UTC),
        )
    finally:
        worker.clear_handlers()
    assert handled is True

    async_session.expire_all()
    refreshed_job = await async_session.get(Job, job_id)
    assert refreshed_job is not None
    assert refreshed_job.status == JOB_STATUS_SUCCEEDED
