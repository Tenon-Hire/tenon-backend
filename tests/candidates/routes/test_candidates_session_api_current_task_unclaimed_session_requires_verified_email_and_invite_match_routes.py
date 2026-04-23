from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_api_utils import *


@pytest.mark.asyncio
async def test_current_task_unclaimed_session_requires_invite_match_and_claims_session_without_email_verification_gate(
    async_client, async_session, override_dependencies
):
    talent_partner = await create_talent_partner(
        async_session, email="unclaimed-id@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="owner@example.com",
        with_default_schedule=True,
    )
    route = f"/api/candidate/session/{cs.id}/current_task"
    headers = {"x-candidate-session-id": str(cs.id)}

    async def _principal_wrong_email():
        return _principal(
            "attacker@example.com",
            sub="candidate-attacker@example.com",
            email_verified=True,
        )

    with override_dependencies({get_principal: _principal_wrong_email}):
        mismatch = await async_client.get(route, headers=headers)
    assert mismatch.status_code == 403
    assert mismatch.json()["errorCode"] == "CANDIDATE_INVITE_EMAIL_MISMATCH"

    async def _principal_unverified():
        return _principal(
            cs.invite_email,
            sub=f"candidate-{cs.invite_email}",
            email_verified=False,
        )

    with override_dependencies({get_principal: _principal_unverified}):
        unverified = await async_client.get(route, headers=headers)
    assert unverified.status_code == 200, unverified.text

    async def _principal_missing_verified():
        return _principal(
            cs.invite_email,
            sub=f"candidate-{cs.invite_email}",
            email_verified=None,
        )

    with override_dependencies({get_principal: _principal_missing_verified}):
        missing_verified = await async_client.get(route, headers=headers)
    assert missing_verified.status_code == 200, missing_verified.text

    expected_sub = "candidate-owner@example.com"

    async def _principal_owner_verified():
        return _principal(
            "  OWNER@EXAMPLE.COM  ",
            sub=expected_sub,
            email_verified=True,
        )

    with override_dependencies({get_principal: _principal_owner_verified}):
        ok = await async_client.get(route, headers=headers)
    assert ok.status_code == 200, ok.text

    await async_session.refresh(cs)
    assert cs.candidate_auth0_sub == expected_sub
    assert cs.claimed_at is not None
