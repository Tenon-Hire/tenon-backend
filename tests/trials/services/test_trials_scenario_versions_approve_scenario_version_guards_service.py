from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_approve_scenario_version_guards(async_session):
    owner = await create_talent_partner(
        async_session, email="scenario-approve-owner@test.com"
    )
    outsider = await create_talent_partner(
        async_session, email="scenario-approve-outsider@test.com"
    )
    sim, _tasks = await create_trial(async_session, created_by=owner)
    (
        _updated_sim,
        regenerated,
        _job,
    ) = await scenario_service.request_scenario_regeneration(
        async_session,
        trial_id=sim.id,
        actor_user_id=owner.id,
    )

    with pytest.raises(HTTPException) as forbidden_exc:
        await scenario_service.approve_scenario_version(
            async_session,
            trial_id=sim.id,
            scenario_version_id=regenerated.id,
            actor_user_id=outsider.id,
        )
    assert forbidden_exc.value.status_code == 403

    with pytest.raises(ApiError) as not_ready_exc:
        await scenario_service.approve_scenario_version(
            async_session,
            trial_id=sim.id,
            scenario_version_id=regenerated.id,
            actor_user_id=owner.id,
        )
    assert not_ready_exc.value.status_code == 409
    assert not_ready_exc.value.error_code == "SCENARIO_NOT_READY"

    regenerated.status = "ready"
    await async_session.commit()

    with pytest.raises(ApiError) as mismatch_exc:
        await scenario_service.approve_scenario_version(
            async_session,
            trial_id=sim.id,
            scenario_version_id=sim.active_scenario_version_id,
            actor_user_id=owner.id,
        )
    assert mismatch_exc.value.status_code == 409
    assert mismatch_exc.value.error_code == "SCENARIO_VERSION_NOT_PENDING"
