from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_regenerate_active_scenario_version_owner_and_active_guards(
    async_session,
):
    owner = await create_talent_partner(
        async_session, email="scenario-regen-owner@test.com"
    )
    outsider = await create_talent_partner(
        async_session, email="scenario-regen-outsider@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=owner)

    with pytest.raises(HTTPException) as excinfo:
        await scenario_service.regenerate_active_scenario_version(
            async_session,
            trial_id=sim.id,
            actor_user_id=outsider.id,
        )
    assert excinfo.value.status_code == 403

    sim.status = "generating"
    sim.active_scenario_version_id = None
    await async_session.commit()
    with pytest.raises(ApiError) as missing_exc:
        await scenario_service.regenerate_active_scenario_version(
            async_session,
            trial_id=sim.id,
            actor_user_id=owner.id,
        )
    assert missing_exc.value.error_code == "SCENARIO_ACTIVE_VERSION_MISSING"
