from __future__ import annotations

import pytest

from tests.shared.http.routes.shared_http_auth_permissions_utils import *


@pytest.mark.asyncio
async def test_candidate_mismatched_email_gets_403(async_client, async_session):
    talent_partner = await create_talent_partner(
        async_session, email="claim403@test.com"
    )
    sim, _ = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(async_session, trial=sim)
    other = await create_candidate_session(
        async_session, trial=sim, invite_email="other@example.com"
    )
    token = f"candidate:{other.invite_email}"

    res = await async_client.get(
        f"/api/candidate/session/{cs.token}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert res.json()["errorCode"] == "CANDIDATE_INVITE_EMAIL_MISMATCH"
