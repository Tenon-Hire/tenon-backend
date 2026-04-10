from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_api_utils import *


@pytest.mark.asyncio
async def test_resolve_expired_token_returns_410(async_client, async_session):
    talent_partner = await create_talent_partner(
        async_session, email="expired-resolve@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        expires_in_days=-1,
        status="not_started",
    )

    res = await async_client.get(
        f"/api/candidate/session/{cs.token}",
        headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
    )
    assert res.status_code == 410
