from __future__ import annotations

import pytest

from tests.shared.http.routes.shared_http_auth_permissions_utils import *


@pytest.mark.asyncio
async def test_invite_token_requires_auth(async_client, async_session):
    recruiter = await create_recruiter(async_session, email="inviteauth@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim)

    res = await async_client.get(f"/api/candidate/session/{cs.token}")
    assert res.status_code == 401
