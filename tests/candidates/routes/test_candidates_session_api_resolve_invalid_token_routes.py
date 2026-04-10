from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_api_utils import *


@pytest.mark.asyncio
async def test_resolve_invalid_token(async_client, async_session):
    talent_partner = await create_talent_partner(
        async_session, email="invalid@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim)
    res = await async_client.get(
        "/api/candidate/session/" + "x" * 24,
        headers={"Authorization": f"Bearer candidate:{cs.invite_email}"},
    )
    assert res.status_code == 404
