from __future__ import annotations

import pytest

from tests.simulations.routes.simulations_lifecycle_api_utils import *


@pytest.mark.asyncio
async def test_invite_requires_active_inviting(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="invite-state@test.com")
    created = await _create_simulation_via_api(
        async_client, async_session, auth_header_factory(recruiter)
    )
    sim_id = created["id"]

    blocked = await async_client.post(
        f"/api/simulations/{sim_id}/invite",
        headers=auth_header_factory(recruiter),
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json() == {
        "detail": "Simulation is not approved for inviting.",
        "errorCode": "SIMULATION_NOT_INVITABLE",
        "retryable": False,
        "details": {"status": "ready_for_review"},
    }

    activate = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=auth_header_factory(recruiter),
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    allowed = await async_client.post(
        f"/api/simulations/{sim_id}/invite",
        headers=auth_header_factory(recruiter),
        json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
    )
    assert allowed.status_code == 200, allowed.text
