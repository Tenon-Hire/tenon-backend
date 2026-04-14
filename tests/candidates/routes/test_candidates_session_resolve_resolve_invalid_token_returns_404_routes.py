from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_resolve_api_utils import *
from tests.trials.routes.trials_scenario_versions_api_utils import _approve_trial


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_resolve_invalid_token_returns_404(async_client, async_session):
    talent_partner_email = "invalidtoken@test.com"
    await _seed_talent_partner(async_session, talent_partner_email)
    sim_id = await _create_trial(async_client, async_session, talent_partner_email)
    await _approve_trial(
        async_client,
        sim_id=sim_id,
        headers={"x-dev-user-email": talent_partner_email},
    )
    activate = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        json={"confirm": True},
        headers={"x-dev-user-email": talent_partner_email},
    )
    assert activate.status_code == 200, activate.text
    invite = await _invite_candidate(async_client, sim_id, talent_partner_email)
    await _claim(async_client, invite["token"], "jane@example.com")
    access_token = "candidate:jane@example.com"

    res = await async_client.get(
        "/api/candidate/session/invalid-token-1234567890",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Invalid invite token"
