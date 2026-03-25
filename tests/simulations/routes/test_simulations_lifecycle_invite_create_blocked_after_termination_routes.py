from __future__ import annotations

import pytest

from tests.simulations.routes.simulations_lifecycle_api_utils import *


@pytest.mark.asyncio
async def test_invite_create_blocked_after_termination(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="invite-stop@test.com")
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

    terminate = await async_client.post(
        f"/api/simulations/{sim_id}/terminate",
        headers=auth_header_factory(recruiter),
        json={"confirm": True},
    )
    assert terminate.status_code == 200, terminate.text

    blocked = await async_client.post(
        f"/api/simulations/{sim_id}/invite",
        headers=auth_header_factory(recruiter),
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["errorCode"] == "SIMULATION_TERMINATED"
