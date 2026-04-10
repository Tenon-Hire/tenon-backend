from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_patch_scenario_version_allows_ready_scenario_status(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-patch-ready-status@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    active = await async_session.get(ScenarioVersion, sim.active_scenario_version_id)
    assert active is not None
    assert sim.status == "active_inviting"
    assert active.status == "ready"

    patched = await scenario_service.patch_scenario_version(
        async_session,
        trial_id=sim.id,
        scenario_version_id=active.id,
        actor_user_id=talent_partner.id,
        updates={"focus_notes": "Edited while scenario status is ready"},
    )
    assert patched.focus_notes == "Edited while scenario status is ready"
