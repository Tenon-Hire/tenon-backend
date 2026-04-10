from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_update_active_scenario_version_without_status_keeps_existing_status(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-update-no-status@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    active = await async_session.get(ScenarioVersion, sim.active_scenario_version_id)
    assert active is not None
    assert active.status == "ready"

    updated = await scenario_service.update_active_scenario_version(
        async_session,
        trial_id=sim.id,
        actor_user_id=talent_partner.id,
        updates={"focus_notes": "Updated without status field"},
    )
    assert updated.focus_notes == "Updated without status field"
    assert updated.status == "ready"
