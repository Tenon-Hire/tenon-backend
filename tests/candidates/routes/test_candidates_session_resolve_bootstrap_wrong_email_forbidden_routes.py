from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_session_resolve_api_utils import *


@pytest.mark.asyncio
async def test_bootstrap_wrong_email_forbidden(async_client, async_session):
    talent_partner_email = "wrongemail@test.com"
    await _seed_talent_partner(async_session, talent_partner_email)
    sim_id = await _create_trial(async_client, async_session, talent_partner_email)
    invite = await _invite_candidate(async_client, sim_id, talent_partner_email)
    other_invite = await _invite_candidate(
        async_client,
        sim_id,
        talent_partner_email,
        invite_email="other@example.com",
    )
    await _claim(async_client, other_invite["token"], "other@example.com")
    access_token = "candidate:other@example.com"

    res = await async_client.get(
        f"/api/candidate/session/{invite['token']}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert res.status_code == 403
    assert res.json()["errorCode"] == "CANDIDATE_INVITE_EMAIL_MISMATCH"
