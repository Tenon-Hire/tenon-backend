from __future__ import annotations

import pytest

from tests.simulations.routes.simulations_lifecycle_api_utils import *


@pytest.mark.asyncio
async def test_invite_resend_blocked_after_termination(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="resend-stop@test.com")
    created = await _create_simulation_via_api(
        async_client, async_session, auth_header_factory(recruiter)
    )
    sim_id = created["id"]

    activate = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=auth_header_factory(recruiter),
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    invite = await async_client.post(
        f"/api/simulations/{sim_id}/invite",
        headers=auth_header_factory(recruiter),
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert invite.status_code == 200, invite.text
    candidate_session_id = invite.json()["candidateSessionId"]

    terminate = await async_client.post(
        f"/api/simulations/{sim_id}/terminate",
        headers=auth_header_factory(recruiter),
        json={"confirm": True},
    )
    assert terminate.status_code == 200, terminate.text

    resend = await async_client.post(
        f"/api/simulations/{sim_id}/candidates/{candidate_session_id}/invite/resend",
        headers=auth_header_factory(recruiter),
    )
    assert resend.status_code == 409, resend.text
    assert resend.json()["errorCode"] == "SIMULATION_TERMINATED"
