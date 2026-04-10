from __future__ import annotations

import pytest

from tests.trials.routes.trials_lifecycle_api_utils import *


@pytest.mark.asyncio
async def test_invite_resend_blocked_after_termination(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="resend-stop@test.com"
    )
    created = await _create_trial_via_api(
        async_client, async_session, auth_header_factory(talent_partner)
    )
    sim_id = created["id"]

    activate = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        headers=auth_header_factory(talent_partner),
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    invite = await async_client.post(
        f"/api/trials/{sim_id}/invite",
        headers=auth_header_factory(talent_partner),
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert invite.status_code == 200, invite.text
    candidate_session_id = invite.json()["candidateSessionId"]

    terminate = await async_client.post(
        f"/api/trials/{sim_id}/terminate",
        headers=auth_header_factory(talent_partner),
        json={"confirm": True},
    )
    assert terminate.status_code == 200, terminate.text

    resend = await async_client.post(
        f"/api/trials/{sim_id}/candidates/{candidate_session_id}/invite/resend",
        headers=auth_header_factory(talent_partner),
    )
    assert resend.status_code == 409, resend.text
    assert resend.json()["errorCode"] == "TRIAL_TERMINATED"
