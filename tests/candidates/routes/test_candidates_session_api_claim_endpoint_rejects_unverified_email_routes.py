from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_api_utils import *


@pytest.mark.asyncio
async def test_claim_endpoint_rejects_unverified_email(
    async_client, async_session, override_dependencies
):
    recruiter = await create_recruiter(async_session, email="verifyfalse@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim)

    async def _override_get_principal():
        return _principal(cs.invite_email, email_verified=False)

    with override_dependencies({get_principal: _override_get_principal}):
        res = await async_client.post(
            f"/api/candidate/session/{cs.token}/claim",
            headers={"Authorization": "Bearer ignored"},
        )
    assert res.status_code == 403
    assert res.json()["errorCode"] == "CANDIDATE_EMAIL_NOT_VERIFIED"
