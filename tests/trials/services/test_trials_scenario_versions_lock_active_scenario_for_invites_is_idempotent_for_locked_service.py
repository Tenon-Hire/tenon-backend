from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_lock_active_scenario_for_invites_is_idempotent_for_locked(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-lock-idempotent@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    active = await async_session.get(ScenarioVersion, sim.active_scenario_version_id)
    assert active is not None
    active.status = "locked"
    active.locked_at = datetime.now(UTC)
    await async_session.commit()

    locked = await scenario_service.lock_active_scenario_for_invites(
        async_session, trial_id=sim.id
    )
    assert locked.id == active.id
    assert locked.status == "locked"
