from __future__ import annotations

import pytest

from tests.simulations.routes.simulations_scenario_versions_api_utils import *


@pytest.mark.asyncio
async def test_mutating_locked_scenario_returns_scenario_locked(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(async_session, email="scenario-mutate@test.com")
    sim_id = await _create_simulation(
        async_client, async_session, auth_header_factory(recruiter)
    )

    activate = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=auth_header_factory(recruiter),
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    invite = await async_client.post(
        f"/api/simulations/{sim_id}/invite",
        headers=auth_header_factory(recruiter),
        json={"candidateName": "Locked", "inviteEmail": "locked@example.com"},
    )
    assert invite.status_code == 200, invite.text

    mutate = await async_client.patch(
        f"/api/simulations/{sim_id}/scenario/active",
        headers=auth_header_factory(recruiter),
        json={"focusNotes": "This should fail"},
    )
    assert mutate.status_code == 409, mutate.text
    assert mutate.json() == {
        "detail": "Scenario version is locked.",
        "errorCode": "SCENARIO_LOCKED",
    }
