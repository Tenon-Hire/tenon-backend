from __future__ import annotations

import pytest

from tests.shared.http.routes.shared_http_auth_permissions_utils import *


@pytest.mark.asyncio
async def test_talent_partner_token_cannot_access_candidate_routes(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="talent_partner@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim)

    res = await async_client.get(
        f"/api/candidate/session/{cs.id}/current_task",
        headers={
            "Authorization": "Bearer talent_partner:talent_partner@test.com",
            "x-candidate-session-id": str(cs.id),
        },
    )
    assert res.status_code == 403
