from __future__ import annotations

import pytest

from tests.talent_partners.services.talent_partners_admin_ops_utils import *


@pytest.mark.asyncio
async def test_requeue_job_dead_letter_requeues_and_clears_lock_state(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="requeue-dead-owner@test.com"
    )
    company = await async_session.get(Company, talent_partner.company_id)
    assert company is not None
    job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_DEAD_LETTER,
        job_type="admin-requeue-dead-unit",
        last_error="demo failure",
        result_json={"failure": True},
        payload_json={"x": 1},
    )
    job.locked_at = datetime.now(UTC) - timedelta(minutes=30)
    job.locked_by = "worker-123"
    await async_session.commit()

    now = datetime(2026, 1, 3, 15, 0, 0)
    result = await admin_ops_service.requeue_job(
        async_session,
        actor=_actor(),
        job_id=job.id,
        reason="dead-letter retry",
        force=False,
        now=now,
    )
    assert result.previous_status == JOB_STATUS_DEAD_LETTER
    assert result.new_status == JOB_STATUS_QUEUED

    refreshed = await async_session.get(type(job), job.id)
    assert refreshed is not None
    assert refreshed.status == JOB_STATUS_QUEUED
    assert refreshed.locked_at is None
    assert refreshed.locked_by is None
    assert refreshed.last_error is None
    assert refreshed.result_json is None
    assert refreshed.next_run_at is not None
    assert _to_utc(refreshed.next_run_at) == _to_utc(now)
