from __future__ import annotations

import pytest

from tests.talent_partners.routes.talent_partners_admin_demo_ops_utils import *


@pytest.mark.asyncio
async def test_reset_candidate_session_writes_audit(
    async_client,
    async_session,
    monkeypatch,
):
    admin_email = "ops-reset@test.com"
    _enable_demo_mode(monkeypatch, allowlist_emails=[admin_email])

    talent_partner = await create_talent_partner(
        async_session, email="owner-reset@test.com"
    )
    trial, _ = await create_trial(async_session, created_by=talent_partner)
    now = datetime.now(UTC).replace(microsecond=0)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="completed",
        candidate_auth0_sub="auth0|candidate-reset",
        claimed_at=now - timedelta(days=1),
        started_at=now - timedelta(hours=8),
        completed_at=now - timedelta(hours=1),
        with_default_schedule=True,
    )
    await async_session.commit()

    response = await async_client.post(
        f"/api/admin/candidate_sessions/{candidate_session.id}/reset",
        json={
            "targetState": "claimed",
            "reason": "Demo reset after wedged session",
            "overrideIfEvaluated": False,
            "dryRun": False,
        },
        headers=_admin_headers(admin_email),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["candidateSessionId"] == candidate_session.id
    assert payload["status"] == "ok"
    assert payload["resetTo"] == "claimed"
    assert isinstance(payload["auditId"], str) and payload["auditId"]

    refreshed = await async_session.get(type(candidate_session), candidate_session.id)
    assert refreshed is not None
    assert refreshed.status == "not_started"
    assert refreshed.claimed_at is not None
    assert refreshed.started_at is None
    assert refreshed.completed_at is None
    assert refreshed.scheduled_start_at is None
    assert refreshed.schedule_locked_at is None

    audit = await async_session.get(AdminActionAudit, payload["auditId"])
    assert audit is not None
    assert audit.action == "candidate_session_reset"
    assert audit.target_type == "candidate_session"
    assert audit.target_id == str(candidate_session.id)
