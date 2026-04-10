from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_update_active_scenario_version_locked_and_missing_guards(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-update-guards@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    active = await async_session.get(ScenarioVersion, sim.active_scenario_version_id)
    assert active is not None
    active.status = "locked"
    await async_session.commit()

    with pytest.raises(ApiError) as locked_exc:
        await scenario_service.update_active_scenario_version(
            async_session,
            trial_id=sim.id,
            actor_user_id=talent_partner.id,
            updates={"focus_notes": "x"},
        )
    assert locked_exc.value.error_code == "SCENARIO_LOCKED"

    sim.status = "generating"
    sim.active_scenario_version_id = None
    await async_session.commit()
    with pytest.raises(ApiError) as missing_exc:
        await scenario_service.update_active_scenario_version(
            async_session,
            trial_id=sim.id,
            actor_user_id=talent_partner.id,
            updates={"focus_notes": "x"},
        )
    assert missing_exc.value.error_code == "SCENARIO_ACTIVE_VERSION_MISSING"
