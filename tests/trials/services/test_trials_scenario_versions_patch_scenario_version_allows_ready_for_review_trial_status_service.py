from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_patch_scenario_version_allows_ready_for_review_trial_status(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-patch-ready-for-review-status@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=talent_partner)
    sim.status = "ready_for_review"
    await async_session.commit()
    active = await async_session.get(ScenarioVersion, sim.active_scenario_version_id)
    assert active is not None
    assert active.status == "ready"

    patched = await scenario_service.patch_scenario_version(
        async_session,
        trial_id=sim.id,
        scenario_version_id=active.id,
        actor_user_id=talent_partner.id,
        updates={"focus_notes": "Edited in ready_for_review trial state"},
    )
    assert patched.focus_notes == "Edited in ready_for_review trial state"
