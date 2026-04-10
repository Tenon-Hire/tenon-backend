from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_api_utils import *


@pytest.mark.asyncio
async def test_current_task_revalidates_claimed_sub_each_request(
    async_client, async_session, override_dependencies
):
    talent_partner = await create_talent_partner(
        async_session, email="claimed-sub@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim)

    claim = await async_client.post(
        f"/api/candidate/session/{cs.token}/claim",
        headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
    )
    assert claim.status_code == 200, claim.text

    async def _override_get_principal():
        return _principal(
            cs.invite_email,
            sub=f"candidate-alt-{cs.invite_email}",
            email_verified=True,
        )

    with override_dependencies({get_principal: _override_get_principal}):
        res = await async_client.get(
            f"/api/candidate/session/{cs.id}/current_task",
            headers={"x-candidate-session-id": str(cs.id)},
        )
    assert res.status_code == 403
    assert res.json()["errorCode"] == "CANDIDATE_SESSION_ALREADY_CLAIMED"
