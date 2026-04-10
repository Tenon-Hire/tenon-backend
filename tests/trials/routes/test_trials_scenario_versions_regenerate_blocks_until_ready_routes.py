from __future__ import annotations

import pytest

from tests.trials.routes.trials_scenario_versions_api_utils import *
from tests.trials.routes.trials_scenario_versions_flow_api_utils import *


@pytest.mark.asyncio
async def test_regenerate_blocks_activation_and_invites_until_ready(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-regen-block@test.com"
    )
    sim_id = await _create_trial(
        async_client, async_session, auth_header_factory(talent_partner)
    )
    headers = auth_header_factory(talent_partner)

    activate = await async_client.post(
        f"/api/trials/{sim_id}/activate",
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
        f"/api/trials/{sim_id}/scenario/regenerate",
        headers=headers,
    )
    assert regenerate.status_code == 200, regenerate.text
    regenerated_scenario_id = regenerate.json()["scenarioVersionId"]

    pending_body = await _trial_detail(async_client, sim_id=sim_id, headers=headers)
    _assert_trial_state(
        pending_body,
        status="ready_for_review",
        active_id=first_scenario.id,
        pending_id=regenerated_scenario_id,
    )

    activate_while_pending = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        headers=headers,
        json={"confirm": True},
    )
    _assert_error(
        activate_while_pending,
        status_code=409,
        error_code="SCENARIO_APPROVAL_PENDING",
    )
    blocked_invite = await async_client.post(
        f"/api/trials/{sim_id}/invite",
        headers=headers,
        json={"candidateName": "Blocked", "inviteEmail": "blocked@example.com"},
    )
    _assert_error(
        blocked_invite,
        status_code=409,
        error_code="SCENARIO_APPROVAL_PENDING",
    )
    approve_early = await async_client.post(
        f"/api/trials/{sim_id}/scenario/{regenerated_scenario_id}/approve",
        headers=headers,
    )
    _assert_error(approve_early, status_code=409, error_code="SCENARIO_NOT_READY")
