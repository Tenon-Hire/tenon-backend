from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_approve_scenario_version_not_found_returns_404(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-approve-missing@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)

    with pytest.raises(HTTPException) as excinfo:
        await scenario_service.approve_scenario_version(
            async_session,
            trial_id=sim.id,
            scenario_version_id=999999,
            actor_user_id=talent_partner.id,
        )
    assert excinfo.value.status_code == 404
