from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_lock_active_scenario_for_invites_requires_active_version(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-lock-missing-active@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    sim.status = "generating"
    sim.active_scenario_version_id = None
    await async_session.commit()

    with pytest.raises(ApiError) as excinfo:
        await scenario_service.lock_active_scenario_for_invites(
            async_session, trial_id=sim.id
        )
    assert excinfo.value.error_code == "SCENARIO_ACTIVE_VERSION_MISSING"
