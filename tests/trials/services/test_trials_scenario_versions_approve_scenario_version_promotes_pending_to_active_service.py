from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_approve_scenario_version_promotes_pending_to_active(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-approve-ok@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    previous_active = sim.active_scenario_version_id
    (
        _updated_sim,
        regenerated,
        _job,
    ) = await scenario_service.request_scenario_regeneration(
        async_session,
        trial_id=sim.id,
        actor_user_id=talent_partner.id,
    )
    regenerated.status = "ready"
    await async_session.commit()

    approved_sim, approved_version = await scenario_service.approve_scenario_version(
        async_session,
        trial_id=sim.id,
        scenario_version_id=regenerated.id,
        actor_user_id=talent_partner.id,
    )

    assert approved_version.id == regenerated.id
    assert approved_sim.pending_scenario_version_id is None
    assert approved_sim.active_scenario_version_id == regenerated.id
    assert approved_sim.active_scenario_version_id != previous_active
    assert approved_sim.status == "active_inviting"

    first_session_active = await async_session.get(ScenarioVersion, previous_active)
    assert first_session_active is not None
