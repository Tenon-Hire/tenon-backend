from __future__ import annotations

import pytest

from tests.recruiters.services.recruiters_admin_ops_utils import *


@pytest.mark.asyncio
async def test_reset_candidate_session_noop_and_sanitized_audit_reason(async_session):
    recruiter = await create_recruiter(async_session, email="reset-noop-owner@test.com")
    simulation, _ = await create_simulation(async_session, created_by=recruiter)
    claimed_at = datetime.now(UTC) - timedelta(minutes=5)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="not_started",
        candidate_auth0_sub="auth0|candidate-reset-noop",
        claimed_at=claimed_at,
    )
    await async_session.commit()

    result = await admin_ops_service.reset_candidate_session(
        async_session,
        actor=_actor(),
        candidate_session_id=candidate_session.id,
        target_state="claimed",
        reason="  keep    claimed \n state ",
        override_if_evaluated=False,
        dry_run=False,
    )
    assert result.status == "ok"
    assert result.audit_id is not None

    audit = await _audit_by_id(async_session, result.audit_id)
    assert audit.payload_json["reason"] == "keep claimed state"
    assert audit.payload_json["noOp"] is True
    assert audit.payload_json["changedFields"] == []
    assert audit.payload_json["targetState"] == "claimed"

    refreshed = await async_session.get(type(candidate_session), candidate_session.id)
    assert refreshed is not None
    assert refreshed.status == "not_started"
    assert refreshed.claimed_at == claimed_at
