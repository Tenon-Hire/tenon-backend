from __future__ import annotations

import pytest

from tests.simulations.routes.simulations_scenario_versions_api_utils import *
from tests.simulations.routes.simulations_scenario_versions_flow_api_utils import *


@pytest.mark.asyncio
async def test_regenerate_approval_promotes_pending_scenario(
    async_client, async_session, auth_header_factory
):
    recruiter = await create_recruiter(
        async_session, email="scenario-regen-approve@test.com"
    )
    sim_id = await _create_simulation(
        async_client, async_session, auth_header_factory(recruiter)
    )
    headers = auth_header_factory(recruiter)

    activate = await async_client.post(
        f"/api/simulations/{sim_id}/activate",
        headers=headers,
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text
    await _invite_candidate(
        async_client,
        sim_id=sim_id,
        headers=headers,
        name="First",
        email="first@example.com",
    )
    first_scenario = await _active_scenario(async_session, sim_id=sim_id)

    regenerate = await async_client.post(
        f"/api/simulations/{sim_id}/scenario/regenerate",
        headers=headers,
    )
    assert regenerate.status_code == 200, regenerate.text
    regenerated_scenario_id = regenerate.json()["scenarioVersionId"]

    handled = await _run_scenario_job(
        async_session,
        worker_id="scenario-versions-regen-worker",
    )
    assert handled is True

    ready_body = await _simulation_detail(async_client, sim_id=sim_id, headers=headers)
    _assert_simulation_state(
        ready_body,
        status="ready_for_review",
        active_id=first_scenario.id,
        pending_id=regenerated_scenario_id,
    )

    approve = await async_client.post(
        f"/api/simulations/{sim_id}/scenario/{regenerated_scenario_id}/approve",
        headers=headers,
    )
    assert approve.status_code == 200, approve.text
    _assert_simulation_state(
        approve.json(),
        status="active_inviting",
        active_id=regenerated_scenario_id,
        pending_id=None,
    )
    approved_detail = await _simulation_detail(
        async_client, sim_id=sim_id, headers=headers
    )
    _assert_simulation_state(
        approved_detail,
        status="active_inviting",
        active_id=regenerated_scenario_id,
        pending_id=None,
    )
