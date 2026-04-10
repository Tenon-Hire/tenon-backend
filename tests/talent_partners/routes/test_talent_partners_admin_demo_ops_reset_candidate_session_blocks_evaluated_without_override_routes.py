from __future__ import annotations

import pytest

from tests.talent_partners.routes.talent_partners_admin_demo_ops_utils import *


@pytest.mark.asyncio
async def test_reset_candidate_session_blocks_evaluated_without_override(
    async_client,
    async_session,
    monkeypatch,
):
    admin_email = "ops-reset-eval@test.com"
    _enable_demo_mode(monkeypatch, allowlist_emails=[admin_email])

    talent_partner = await create_talent_partner(
        async_session, email="owner-reset-eval@test.com"
    )
    trial, _ = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="completed",
        candidate_auth0_sub="auth0|candidate-eval",
        claimed_at=datetime.now(UTC) - timedelta(days=2),
    )
    evaluation_run = EvaluationRun(
        candidate_session_id=candidate_session.id,
        scenario_version_id=candidate_session.scenario_version_id,
        status=EVALUATION_RUN_STATUS_COMPLETED,
        started_at=datetime.now(UTC) - timedelta(hours=2),
        completed_at=datetime.now(UTC) - timedelta(hours=1),
        model_name="eval-model",
        model_version="v1",
        prompt_version="p1",
        rubric_version="r1",
        day2_checkpoint_sha="day2sha",
        day3_final_sha="day3sha",
        cutoff_commit_sha="cutoffsha",
        transcript_reference="transcript://test",
    )
    async_session.add(evaluation_run)
    await async_session.commit()

    blocked = await async_client.post(
        f"/api/admin/candidate_sessions/{candidate_session.id}/reset",
        json={
            "targetState": "claimed",
            "reason": "Reset evaluated session",
            "overrideIfEvaluated": False,
            "dryRun": False,
        },
        headers=_admin_headers(admin_email),
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["errorCode"] == "UNSAFE_OPERATION"

    allowed = await async_client.post(
        f"/api/admin/candidate_sessions/{candidate_session.id}/reset",
        json={
            "targetState": "claimed",
            "reason": "Override evaluated reset for demo",
            "overrideIfEvaluated": True,
            "dryRun": False,
        },
        headers=_admin_headers(admin_email),
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["status"] == "ok"
