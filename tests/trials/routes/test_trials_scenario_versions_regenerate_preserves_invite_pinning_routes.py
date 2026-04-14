from __future__ import annotations

import pytest

from tests.trials.routes.trials_scenario_versions_api_utils import *
from tests.trials.routes.trials_scenario_versions_flow_api_utils import *


@pytest.mark.asyncio
async def test_regenerate_preserves_existing_invite_pinning(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-regen-pinning@test.com"
    )
    sim_id = await _create_trial(
        async_client, async_session, auth_header_factory(talent_partner)
    )
    headers = auth_header_factory(talent_partner)

    await _approve_trial(async_client, sim_id=sim_id, headers=headers)
    activate = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        headers=headers,
        json={"confirm": True},
    )
    assert activate.status_code == 200, activate.text

    first_candidate_session_id = await _invite_candidate(
        async_client,
        sim_id=sim_id,
        headers=headers,
        name="First",
        email="first@example.com",
    )
    first_scenario = await _active_scenario(async_session, sim_id=sim_id)
    regenerate = await async_client.post(
        f"/api/trials/{sim_id}/scenario/regenerate",
        headers=headers,
    )
    assert regenerate.status_code == 200, regenerate.text
    regenerated_scenario_id = regenerate.json()["scenarioVersionId"]
    handled = await _run_scenario_job(
        async_session,
        worker_id="scenario-versions-regen-worker",
    )
    assert handled is True
    approve = await async_client.post(
        f"/api/trials/{sim_id}/scenario/{regenerated_scenario_id}/approve",
        headers=headers,
    )
    assert approve.status_code == 200, approve.text

    re_activate = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        headers=headers,
        json={"confirm": True},
    )
    assert re_activate.status_code == 200, re_activate.text

    second_candidate_session_id = await _invite_candidate(
        async_client,
        sim_id=sim_id,
        headers=headers,
        name="Second",
        email="second@example.com",
    )
    first_candidate_session = await _candidate_session_by_id(
        async_session,
        session_id=first_candidate_session_id,
    )
    second_candidate_session = await _candidate_session_by_id(
        async_session,
        session_id=second_candidate_session_id,
    )
    assert first_candidate_session.scenario_version_id == first_scenario.id
    assert second_candidate_session.scenario_version_id == regenerated_scenario_id
