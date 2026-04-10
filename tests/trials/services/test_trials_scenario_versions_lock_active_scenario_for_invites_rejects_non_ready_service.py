from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_lock_active_scenario_for_invites_rejects_non_ready(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-lock-nonready@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    active = await async_session.get(ScenarioVersion, sim.active_scenario_version_id)
    assert active is not None
    active.status = "draft"
    await async_session.commit()

    with pytest.raises(ApiError) as excinfo:
        await scenario_service.lock_active_scenario_for_invites(
            async_session, trial_id=sim.id
        )
    assert excinfo.value.error_code == "SCENARIO_NOT_READY"
