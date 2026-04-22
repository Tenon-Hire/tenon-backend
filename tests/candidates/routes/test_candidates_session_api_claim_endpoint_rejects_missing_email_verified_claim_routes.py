from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_api_utils import *


@pytest.mark.asyncio
async def test_claim_endpoint_allows_missing_email_verified_claim(
    async_client, async_session, override_dependencies
):
    talent_partner = await create_talent_partner(
        async_session, email="verifymissing@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim)

    async def _override_get_principal():
        return _principal(cs.invite_email, email_verified=None)

    with override_dependencies({get_principal: _override_get_principal}):
        res = await async_client.post(
            f"/api/candidate/session/{cs.token}/claim",
            headers={"Authorization": "Bearer ignored"},
        )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "in_progress"
