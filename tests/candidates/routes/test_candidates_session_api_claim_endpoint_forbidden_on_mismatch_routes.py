from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_api_utils import *


@pytest.mark.asyncio
async def test_claim_endpoint_forbidden_on_mismatch(async_client, async_session):
    talent_partner = await create_talent_partner(
        async_session, email="claimfail@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim)
    await create_candidate_session(
        async_session,
        trial=sim,
        invite_email="other@example.com",
    )

    res = await async_client.get(
        f"/api/candidate/session/{cs.token}",
        headers={"Authorization": "Bearer candidate:other@example.com"},
    )
    assert res.status_code == 403
    body = res.json()
    assert body["errorCode"] == "CANDIDATE_INVITE_EMAIL_MISMATCH"
    assert body["retryable"] is False
    assert body["details"] == {}
