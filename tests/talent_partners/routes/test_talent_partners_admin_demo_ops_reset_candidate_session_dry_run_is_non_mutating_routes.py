from __future__ import annotations

import pytest

from tests.talent_partners.routes.talent_partners_admin_demo_ops_utils import *


@pytest.mark.asyncio
async def test_reset_candidate_session_dry_run_is_non_mutating(
    async_client,
    async_session,
    monkeypatch,
):
    admin_email = "ops-reset-dry-run@test.com"
    _enable_demo_mode(monkeypatch, allowlist_emails=[admin_email])

    talent_partner = await create_talent_partner(
        async_session, email="owner-reset-dry@test.com"
    )
    trial, _ = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="in_progress",
        candidate_auth0_sub="auth0|candidate-dry",
        claimed_at=datetime.now(UTC) - timedelta(days=1),
        started_at=datetime.now(UTC) - timedelta(hours=6),
    )
    candidate_session_id = candidate_session.id
    await async_session.commit()

    response = await async_client.post(
        f"/api/admin/candidate_sessions/{candidate_session.id}/reset",
        json={
            "targetState": "not_started",
            "reason": "Dry run reset",
            "overrideIfEvaluated": False,
            "dryRun": True,
        },
        headers=_admin_headers(admin_email),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "dry_run"
    assert payload["auditId"] is None

    await async_session.rollback()
    refreshed = await async_session.get(CandidateSession, candidate_session_id)
    assert refreshed is not None
    assert refreshed.status == "in_progress"
    assert refreshed.started_at is not None

    audits = (
        (
            await async_session.execute(
                select(AdminActionAudit).where(
                    AdminActionAudit.target_id == str(candidate_session.id),
                    AdminActionAudit.action == "candidate_session_reset",
                )
            )
        )
        .scalars()
        .all()
    )
    assert audits == []
