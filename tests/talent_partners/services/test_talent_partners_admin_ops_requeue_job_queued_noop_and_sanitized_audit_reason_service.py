from __future__ import annotations

import pytest

from tests.talent_partners.services.talent_partners_admin_ops_utils import *


@pytest.mark.asyncio
async def test_requeue_job_queued_noop_and_sanitized_audit_reason(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="requeue-noop-owner@test.com"
    )
    company = await async_session.get(Company, talent_partner.company_id)
    assert company is not None
    job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_QUEUED,
        job_type="admin-requeue-noop-unit",
    )
    await async_session.commit()

    result = await admin_ops_service.requeue_job(
        async_session,
        actor=_actor(),
        job_id=job.id,
        reason="  keep    queued \n state ",
        force=False,
    )
    assert result.previous_status == JOB_STATUS_QUEUED
    assert result.new_status == JOB_STATUS_QUEUED
    audit = await _audit_by_id(async_session, result.audit_id)
    assert audit.payload_json["reason"] == "keep queued state"
    assert audit.payload_json["noOp"] is True
    assert audit.payload_json["newStatus"] == JOB_STATUS_QUEUED
