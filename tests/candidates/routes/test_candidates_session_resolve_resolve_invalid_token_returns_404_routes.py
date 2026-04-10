from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_resolve_api_utils import *


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_resolve_invalid_token_returns_404(async_client, async_session):
    talent_partner_email = "invalidtoken@test.com"
    await _seed_talent_partner(async_session, talent_partner_email)
    sim_id = await _create_trial(async_client, async_session, talent_partner_email)
    invite = await _invite_candidate(async_client, sim_id, talent_partner_email)
    await _claim(async_client, invite["token"], "jane@example.com")
    access_token = "candidate:jane@example.com"

    res = await async_client.get(
        "/api/candidate/session/invalid-token-1234567890",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Invalid invite token"
