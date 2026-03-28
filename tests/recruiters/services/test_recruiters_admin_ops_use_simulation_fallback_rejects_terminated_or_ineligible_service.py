from __future__ import annotations

import pytest

from tests.recruiters.services.recruiters_admin_ops_utils import *


@pytest.mark.asyncio
async def test_use_simulation_fallback_rejects_terminated_or_ineligible(async_session):
    recruiter = await create_recruiter(
        async_session, email="fallback-rejects-owner@test.com"
    )
    simulation, _ = await create_simulation(async_session, created_by=recruiter)
    scenario_v2 = await _create_scenario_version(
        async_session,
        simulation_id=simulation.id,
        version_index=2,
        status=SCENARIO_VERSION_STATUS_GENERATING,
    )
    await async_session.commit()

    with pytest.raises(ApiError) as ineligible:
        await admin_ops_service.use_simulation_fallback_scenario(
            async_session,
            actor=_actor(),
            simulation_id=simulation.id,
            scenario_version_id=scenario_v2.id,
            apply_to="future_invites_only",
            reason="ineligible scenario",
            dry_run=False,
        )
    assert ineligible.value.status_code == 409
    assert ineligible.value.error_code == admin_ops_service.UNSAFE_OPERATION_ERROR_CODE

    simulation.status = SIMULATION_STATUS_TERMINATED
    await async_session.commit()
    with pytest.raises(ApiError) as terminated:
        await admin_ops_service.use_simulation_fallback_scenario(
            async_session,
            actor=_actor(),
            simulation_id=simulation.id,
            scenario_version_id=scenario_v2.id,
            apply_to="future_invites_only",
            reason="terminated simulation",
            dry_run=False,
        )
    assert terminated.value.status_code == 409
