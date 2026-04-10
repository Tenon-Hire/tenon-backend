from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_lock_active_scenario_for_invites_rejects_mismatched_active(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-lock-mismatch@test.com"
    )
    sim1, _tasks1 = await create_trial(async_session, created_by=talent_partner)
    sim2, _tasks2 = await create_trial(async_session, created_by=talent_partner)
    sim1.active_scenario_version_id = sim2.active_scenario_version_id
    await async_session.commit()

    with pytest.raises(ApiError) as excinfo:
        await scenario_service.lock_active_scenario_for_invites(
            async_session, trial_id=sim1.id
        )
    assert excinfo.value.error_code == "SCENARIO_ACTIVE_VERSION_MISSING"
